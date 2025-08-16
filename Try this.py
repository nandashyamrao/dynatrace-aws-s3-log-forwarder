#!/usr/bin/env python3
"""
download_new_dashboards.py

Dynatrace OAuth -> Download *New* Dashboards (v2) as JSON

What it does
------------
- Gets an OAuth token using client credentials
- Lists dashboards via /api/v2/dashboards (pagination supported)
- Downloads each dashboard's full definition: /api/v2/dashboards/{id}
- Saves to ./dashboards/ as '<name>__<id>.json' (sanitized)
- Writes an index file 'dashboards_index.md'
- Certificate handling baked in (enterprise-friendly)

Config sources (in order)
-------------------------
1) Environment variables:
   DT_CLIENT_ID, DT_CLIENT_SECRET, DT_ENV_URL, DT_ACCOUNT_URN
   Optional: DT_SSO_URL, REQUESTS_CA_BUNDLE, DT_CA_BUNDLE
2) ~/.dynatraceoauth file with lines like:
   client_id:...
   client_secret:...
   env_url:https://<tenant>.live.dynatrace.com
   account_urn:urn:dtaccount:...
   (optional) sso_url:https://sso.dynatrace.com/sso/oauth2/token
   (optional) sfcacerts:/path/to/cacerts.crt  (or directory)

Usage
-----
  python3 download_new_dashboards.py
  python3 download_new_dashboards.py --out ./dashboards --limit 50

Requires
--------
  pip install requests
"""

import os
import sys
import json
import time
import argparse
import pathlib
import re
from typing import Dict, Any, Optional, Tuple, List

import requests


# --------- Config & cert helpers ---------

DOTFILE = pathlib.Path.home() / ".dynatraceoauth"

def read_dotfile() -> Dict[str, str]:
    m: Dict[str, str] = {}
    if DOTFILE.exists():
        for line in DOTFILE.read_text(encoding="utf-8").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                m[k.strip()] = v.strip()
    return m

def env_or_dot(name_env: str, dot_key: str, fallback: Optional[str]=None) -> Optional[str]:
    val = os.environ.get(name_env)
    if val:
        return val
    dot = read_dotfile()
    return dot.get(dot_key, fallback)

def pick_cert_verify() -> Optional[str] or bool:
    """
    Cert resolution strategy:
    1) REQUESTS_CA_BUNDLE (file)
    2) DT_CA_BUNDLE (file or dir; if dir, prefer '<dir>/cacerts.crt', else try any .crt/.pem)
    3) ~/.sfacacerts/cacerts.crt
    4) True  (system defaults)
    """
    # 1) REQUESTS_CA_BUNDLE wins
    cab = os.environ.get("REQUESTS_CA_BUNDLE")
    if cab and pathlib.Path(cab).exists():
        return cab

    # 2) DT_CA_BUNDLE can be file or dir
    dtcab = os.environ.get("DT_CA_BUNDLE")
    if dtcab:
        p = pathlib.Path(dtcab)
        if p.is_file():
            return str(p)
        if p.is_dir():
            # Prefer cacerts.crt
            pref = p / "cacerts.crt"
            if pref.exists():
                return str(pref)
            # else pick first *.crt or *.pem
            for candidate in p.iterdir():
                if candidate.suffix.lower() in (".crt", ".pem") and candidate.is_file():
                    return str(candidate)

    # 3) ~/.sfacacerts/cacerts.crt
    home_bundle = pathlib.Path.home() / "sfacacerts" / "cacerts.crt"
    if home_bundle.exists():
        return str(home_bundle)

    # 4) system
    return True


# --------- OAuth & API ---------

def discover_sso_url(env_url: str, override: Optional[str]) -> str:
    """
    Default to global SSO unless user overrides with DT_SSO_URL or dotfile.
    """
    if override:
        return override.rstrip("/")
    # Safe default for SaaS:
    return "https://sso.dynatrace.com/sso/oauth2/token"

def get_token(env_url: str,
              client_id: str,
              client_secret: str,
              account_urn: str,
              sso_url: Optional[str] = None,
              verify=None,
              timeout=30) -> str:
    token_url = discover_sso_url(env_url, sso_url)
    # Dynatrace accepts standard client_credentials. Scopes are example defaults that work for dashboards.
    # Add/remove as needed for your tenant policies.
    scopes = "app-engine:apps:read dynatrace.environment.read"

    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        # These extras are typically accepted; ignored if not needed:
        "scope": scopes,
        "resource": env_url,
        "audience": account_urn,
    }

    resp = requests.post(token_url, data=data, timeout=timeout, verify=verify)
    # Helpful error message
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        msg = ""
        try:
            msg = json.dumps(resp.json(), indent=2)
        except Exception:
            msg = resp.text
        raise SystemExit(f"[OAuth] Token request failed ({resp.status_code}).\nURL: {token_url}\nBody:\n{msg}") from e

    tok = resp.json().get("access_token")
    if not tok:
        raise SystemExit("[OAuth] No access_token in token response.")
    return tok


def list_dashboards(env_url: str,
                    token: str,
                    verify=None,
                    page_size=200,
                    limit: Optional[int]=None) -> List[Dict[str, Any]]:
    """
    Calls /api/v2/dashboards (New Dashboards) until exhausted or 'limit' reached.
    """
    base = env_url.rstrip("/")
    url = f"{base}/api/v2/dashboards"
    headers = {"Authorization": f"Bearer {token}"}
    params: Dict[str, Any] = {"pageSize": page_size}

    results: List[Dict[str, Any]] = []
    next_key = None

    while True:
        if next_key:
            params = {"nextPageKey": next_key}
        resp = requests.get(url, headers=headers, params=params, verify=verify, timeout=60)
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            raise SystemExit(f"[List] Failed {resp.status_code}: {resp.text}") from e

        payload = resp.json()
        items = payload.get("dashboards") or payload.get("items") or []
        results.extend(items)

        if limit and len(results) >= limit:
            return results[:limit]

        next_key = payload.get("nextPageKey")
        if not next_key:
            break

    return results


def get_dashboard(env_url: str, token: str, dash_id: str, verify=None) -> Dict[str, Any]:
    base = env_url.rstrip("/")
    url = f"{base}/api/v2/dashboards/{dash_id}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, verify=verify, timeout=60)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise SystemExit(f"[Get] {dash_id} failed {resp.status_code}: {resp.text}") from e
    return resp.json()


# --------- Output helpers ---------

def sanitize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^\w\s\-\.]+", "", name)
    name = re.sub(r"\s+", "_", name)
    return name[:120] if name else "dashboard"

def write_index_md(out_dir: pathlib.Path, dashboards: List[Tuple[str,str,str]]):
    """
    dashboards: list of tuples (id, name, filename)
    """
    out = []
    out.append("# Dynatrace — New Dashboards (v2)\n\n")
    out.append(f"_Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}. Total: **{len(dashboards)}**._\n\n")
    out.append("| # | Dashboard Name | ID | File |\n|---:|---|---|---|\n")
    for i, (did, name, fname) in enumerate(dashboards, 1):
        out.append(f"| {i} | {name} | `{did}` | `{fname}` |\n")
    (out_dir / "dashboards_index.md").write_text("".join(out), encoding="utf-8")


# --------- Main ---------

def main():
    ap = argparse.ArgumentParser(description="Download *New* Dynatrace Dashboards (v2) to JSON files.")
    ap.add_argument("--out", default="./dashboards", help="Output folder (default: ./dashboards)")
    ap.add_argument("--limit", type=int, default=None, help="Max dashboards to fetch (default: all)")
    ap.add_argument("--pagesize", type=int, default=200, help="List page size (default: 200)")
    args = ap.parse_args()

    # Load config
    client_id    = env_or_dot("DT_CLIENT_ID",    "client_id")
    client_secret= env_or_dot("DT_CLIENT_SECRET","client_secret")
    env_url      = env_or_dot("DT_ENV_URL",      "env_url")
    account_urn  = env_or_dot("DT_ACCOUNT_URN",  "account_urn")
    sso_url      = env_or_dot("DT_SSO_URL",      "sso_url")

    missing = [k for k,v in [
        ("DT_CLIENT_ID", client_id),
        ("DT_CLIENT_SECRET", client_secret),
        ("DT_ENV_URL", env_url),
        ("DT_ACCOUNT_URN", account_urn),
    ] if not v]
    if missing:
        raise SystemExit(
            "Missing required config: " + ", ".join(missing) +
            "\nSet as environment variables or in ~/.dynatraceoauth"
        )

    verify = pick_cert_verify()

    # OAuth
    token = get_token(env_url, client_id, client_secret, account_urn, sso_url=sso_url, verify=verify)

    # List dashboards (new/v2)
    items = list_dashboards(env_url, token, verify=verify, page_size=args.pagesize, limit=args.limit)
    if not items:
        print("No new (v2) dashboards found.")
        return

    out_dir = pathlib.Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    collected: List[Tuple[str,str,str]] = []

    for item in items:
        did = item.get("id") or item.get("dashboardId")
        name = item.get("name") or item.get("dashboardName") or "dashboard"
        if not did:
            continue

        detail = get_dashboard(env_url, token, did, verify=verify)

        safe = sanitize_name(name)
        fname = f"{safe}__{did}.json"
        (out_dir / fname).write_text(json.dumps(detail, indent=2, ensure_ascii=False), encoding="utf-8")
        collected.append((did, name, fname))
        print(f"Saved: {fname}")

    write_index_md(out_dir, collected)
    print(f"\nDone. JSON files + 'dashboards_index.md' are in: {out_dir}")

if __name__ == "__main__":
    main()
