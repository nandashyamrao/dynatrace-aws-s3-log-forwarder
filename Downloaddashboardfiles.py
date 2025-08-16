#!/usr/bin/env python3
"""
Fetch Dynatrace "new" dashboards (Document Service) via OAuth.

Reads OAuth client credentials, environment URL, and optional CA certs
from ~/.dynatraceoauth (key: value format). Example:

    client_id: dtos02...
    client_secret: abc123...
    env_url: https://<tenant>.live.dynatrace.com
    account_urn: urn:dtaccount:...
    sfcacerts: /Users/you/path/to/cacerts.pem   # optional

Exports all dashboards into ./dashboards_export_new/ as JSON.
"""

import os, sys, json, requests, pathlib

DOTFILE = pathlib.Path.home() / ".dynatraceoauth"
EXPORT_DIR = pathlib.Path("./dashboards_export_new")
TOKEN_URL = "https://sso.dynatrace.com/sso/oauth2/token"


def load_oauth_config(path=DOTFILE):
    """Read simple key: value config file into dict"""
    cfg = {}
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}, create with client_id, client_secret, env_url, account_urn")
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        cfg[k.strip()] = v.strip()
    return cfg


def get_token(cfg: dict) -> str:
    data = {
        "grant_type": "client_credentials",
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "resource": cfg.get("account_urn"),
    }
    verify = cfg.get("sfcacerts") or True
    r = requests.post(TOKEN_URL, data=data, verify=verify)
    r.raise_for_status()
    return r.json()["access_token"]


def fetch_dashboards(cfg: dict, token: str):
    verify = cfg.get("sfcacerts") or True
    env_url = cfg["env_url"].rstrip("/")
    headers = {"Authorization": f"Bearer {token}"}

    dashboards = []
    url = f"{env_url}/platform/document/v1/documents"
    params = {"documentType": "dashboard"}
    while url:
        r = requests.get(url, headers=headers, params=params, verify=verify)
        r.raise_for_status()
        data = r.json()
        dashboards.extend(data.get("items", []))
        url = data.get("nextPageKey")
        if url:
            url = f"{env_url}/platform/document/v1/documents?nextPageKey={url}"
        params = None
    return dashboards


def fetch_dashboard(cfg: dict, token: str, doc_id: str):
    verify = cfg.get("sfcacerts") or True
    env_url = cfg["env_url"].rstrip("/")
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{env_url}/platform/document/v1/documents/{doc_id}"
    r = requests.get(url, headers=headers, verify=verify)
    r.raise_for_status()
    return r.json()


def main():
    cfg = load_oauth_config()
    token = get_token(cfg)
    dashboards = fetch_dashboards(cfg, token)

    EXPORT_DIR.mkdir(exist_ok=True)
    (EXPORT_DIR / "index.json").write_text(json.dumps(dashboards, indent=2), encoding="utf-8")

    for d in dashboards:
        doc_id = d["id"]
        detail = fetch_dashboard(cfg, token, doc_id)
        fname = EXPORT_DIR / f"{doc_id}.json"
        fname.write_text(json.dumps(detail, indent=2), encoding="utf-8")
        print(f"Saved {fname}")

    print(f"Exported {len(dashboards)} dashboards -> {EXPORT_DIR}")


if __name__ == "__main__":
    main()
