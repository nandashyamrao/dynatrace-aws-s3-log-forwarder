#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynatrace Dashboards Export via OAuth2 (client credentials)

What this script does
- Obtains an OAuth2 access token from Dynatrace SSO (client credentials grant).
- Calls the Dashboards (Classic) Configuration API to list dashboard IDs.
- Downloads each dashboard JSON to ./dashboards_export/<id>.json
- Works behind corporate TLS by letting you point to a custom CA bundle (e.g., StateFarm certs).

Environment variables (required)
  DT_OAUTH_CLIENT_ID     = your OAuth client id
  DT_OAUTH_CLIENT_SECRET = your OAuth client secret
  DT_ENV_URL             = https://<env-id>.live.dynatrace.com  (your tenant URL)
  DT_ACCOUNT_URN         = urn:dtaccount:<your-account-uuid>    (required for OAuth client credentials)
    Example: urn:dtaccount:12a34567-8901-2bc3-d45e-6f7g8h90123i

Optional environment variables
  DT_OAUTH_TOKEN_URL     = override token URL (default: https://sso.dynatrace.com/sso/oauth2/token)
  DT_CA_BUNDLE           = path to a PEM file with corporate root CAs (e.g., StateFarm certs)
                           (Alternatively you can set REQUESTS_CA_BUNDLE which requests honors globally.)
  DT_CLIENT_CERT         = path to a client certificate PEM (for rare mTLS setups)
  DT_CLIENT_KEY          = path to the client private key PEM (if separate from DT_CLIENT_CERT)
  HTTPS_PROXY / HTTP_PROXY (standard proxy env vars if needed)

Notes on permissions
- Your OAuth client must have permissions to read configuration (dashboards). In classic API docs
  this is “ReadConfig”; with OAuth clients this is granted by your Dynatrace admin on the client.
- Token request uses `resource=DT_ACCOUNT_URN` as recommended by Dynatrace docs for SSO.
"""
import os
import sys
import json
import time
import pathlib
import typing as t
import requests
from urllib.parse import urljoin

TOKEN_URL_DEFAULT = "https://sso.dynatrace.com/sso/oauth2/token"

def getenv_req(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise SystemExit(f"Missing required environment variable: {name}")
    return v

def build_session() -> requests.Session:
    s = requests.Session()
    s.request = _with_defaults(s.request, timeout=30)
    return s

def _with_defaults(func, **defaults):
    def wrapper(method, url, **kwargs):
        for k, v in defaults.items():
            kwargs.setdefault(k, v)
        return func(method, url, **kwargs)
    return wrapper

def get_tls_kwargs() -> dict:
    tls: dict = {}
    ca = os.getenv("DT_CA_BUNDLE") or os.getenv("REQUESTS_CA_BUNDLE")
    if ca:
        tls["verify"] = ca
    client_cert = os.getenv("DT_CLIENT_CERT")
    client_key  = os.getenv("DT_CLIENT_KEY")
    if client_cert and client_key:
        tls["cert"] = (client_cert, client_key)
    elif client_cert:
        tls["cert"] = client_cert
    return tls

def request_token(session: requests.Session, *, token_url: str, client_id: str, client_secret: str, account_urn: str) -> str:
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "resource": account_urn,
    }
    tls = get_tls_kwargs()
    r = session.post(token_url, data=data, **tls)
    try:
        r.raise_for_status()
    except Exception as e:
        raise SystemExit(f"Token request failed: {e}\nResponse: {r.text}") from e
    js = r.json()
    token = js.get("access_token")
    if not token:
        raise SystemExit(f"No access_token in token response: {js}")
    return token

def get_all_dashboards(session: requests.Session, *, env_url: str, headers: dict) -> t.List[dict]:
    url = urljoin(env_url.rstrip("/") + "/", "api/config/v1/dashboards")
    dashboards: t.List[dict] = []
    next_key = None
    tls = get_tls_kwargs()
    while True:
        params = {}
        if next_key:
            params["nextPageKey"] = next_key
        r = session.get(url, headers=headers, params=params, **tls)
        r.raise_for_status()
        data = r.json()
        dashboards.extend(data.get("dashboards", []))
        next_key = data.get("nextPageKey")
        if not next_key:
            break
    return dashboards

def download_dashboard(session: requests.Session, *, env_url: str, dashboard_id: str, headers: dict) -> dict:
    url = urljoin(env_url.rstrip("/") + "/", f"api/config/v1/dashboards/{dashboard_id}")
    tls = get_tls_kwargs()
    r = session.get(url, headers=headers, **tls)
    r.raise_for_status()
    return r.json()

def sanitize_filename(name: str) -> str:
    bad = '<>:"/\\|?*'
    for ch in bad:
        name = name.replace(ch, "_")
    return name.strip()[:150] or "dashboard"

def main():
    client_id     = getenv_req("DT_OAUTH_CLIENT_ID")
    client_secret = getenv_req("DT_OAUTH_CLIENT_SECRET")
    env_url       = getenv_req("DT_ENV_URL")
    account_urn   = getenv_req("DT_ACCOUNT_URN")  # urn:dtaccount:<uuid>
    token_url     = os.getenv("DT_OAUTH_TOKEN_URL", TOKEN_URL_DEFAULT).strip()

    session = build_session()

    print(f"Issuing token from {token_url} for {account_urn} ...")
    token = request_token(session, token_url=token_url, client_id=client_id,
                          client_secret=client_secret, account_urn=account_urn)
    headers = {"Authorization": f"Bearer {token}"}

    print("Listing dashboards ...")
    dashboards = get_all_dashboards(session, env_url=env_url, headers=headers)
    print(f"Found {len(dashboards)} dashboards")

    outdir = pathlib.Path("dashboards_export")
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "index.json").write_text(json.dumps(dashboards, indent=2), encoding="utf-8")

    for d in dashboards:
        did = d.get("id")
        dname = d.get("name", "") or ""
        safe_name = sanitize_filename(dname)
        fname = f"{did}.json" if did else f"{safe_name}.json"
        print(f"Downloading: {dname or did} -> {fname}")
        try:
            dj = download_dashboard(session, env_url=env_url, dashboard_id=did, headers=headers)
        except requests.HTTPError as e:
            print(f"  ! Failed {did}: {e}")
            continue
        (outdir / fname).write_text(json.dumps(dj, indent=2), encoding="utf-8")

    print(f"✅ Done. Files in {outdir.resolve()}")

if __name__ == "__main__":
    main()
