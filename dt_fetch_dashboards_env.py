#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynatrace NEW Dashboards Exporter (env-based)
---------------------------------------------
Reads credentials from environment variables and exports all NEW dashboards
(Document Service) to ./dashboards_export_new/.

Required env vars:
  DT_CLIENT_ID        - OAuth client id
  DT_CLIENT_SECRET    - OAuth client secret
  DT_ENV_URL          - Dynatrace environment base URL (e.g., https://abc123.live.dynatrace.com)
  DT_ACCOUNT_URN      - Account URN (urn:dtaccount:<uuid>)

Optional env vars:
  DT_OAUTH_TOKEN_URL  - Defaults to https://sso.dynatrace.com/sso/oauth2/token
  DT_CA_BUNDLE        - Path to PEM bundle for TLS verification (e.g., corporate CA)
  REQUESTS_CA_BUNDLE  - Same as above (requests standard)
  DT_SFCACERTS        - Alias for CA bundle path (if set, takes precedence)
  DT_NAME_IN_FILENAME - If "1", filename will be '<sanitized-name>__<id>.json'

Usage:
  export DT_CLIENT_ID=...
  export DT_CLIENT_SECRET=...
  export DT_ENV_URL=https://...live.dynatrace.com
  export DT_ACCOUNT_URN=urn:dtaccount:...
  python3 dt_fetch_dashboards_env.py
"""
import os, json, time, typing as t, pathlib, requests, re
from urllib.parse import urljoin

TOKEN_URL_DEFAULT = "https://sso.dynatrace.com/sso/oauth2/token"

def getenv_req(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise SystemExit(f"Missing required environment variable: {name}")
    return v

def get_verify() -> t.Union[str, bool]:
    # precedence: DT_SFCACERTS > DT_CA_BUNDLE > REQUESTS_CA_BUNDLE > True
    return (
        os.getenv("DT_SFCACERTS")
        or os.getenv("DT_CA_BUNDLE")
        or os.getenv("REQUESTS_CA_BUNDLE")
        or True
    )

def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:120] if name else "dashboard"

def request_token(*, token_url: str, client_id: str, client_secret: str, account_urn: str) -> str:
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "resource": account_urn,
    }
    r = requests.post(token_url, data=data, verify=get_verify(), timeout=30)
    r.raise_for_status()
    js = r.json()
    tok = js.get("access_token")
    if not tok:
        raise SystemExit(f"No access_token in token response: {js}")
    return tok

def list_new_dashboards(*, env_url: str, headers: dict) -> t.List[dict]:
    base = env_url.rstrip('/') + '/'
    url = urljoin(base, "platform/document/v1/documents")
    params = {"filter": "type='dashboard'"}
    out: t.List[dict] = []
    while True:
        r = requests.get(url, headers=headers, params=params, verify=get_verify(), timeout=30)
        r.raise_for_status()
        data = r.json()
        items = data.get("items") or data.get("documents") or data.get("results") or []
        if isinstance(items, list):
            out.extend(items)
        next_key = data.get("nextPageKey") or data.get("next_page_key") or data.get("nextToken")
        if not next_key:
            break
        params = {"nextPageKey": next_key}
    return out

def get_document(*, env_url: str, doc_id: str, headers: dict) -> dict:
    base = env_url.rstrip('/') + '/'
    url = urljoin(base, f"platform/document/v1/documents/{doc_id}")
    r = requests.get(url, headers=headers, verify=get_verify(), timeout=30)
    r.raise_for_status()
    return r.json()

def main():
    client_id = getenv_req("DT_CLIENT_ID")
    client_secret = getenv_req("DT_CLIENT_SECRET")
    env_url = getenv_req("DT_ENV_URL")
    account_urn = getenv_req("DT_ACCOUNT_URN")
    token_url = os.getenv("DT_OAUTH_TOKEN_URL", TOKEN_URL_DEFAULT).strip()

    token = request_token(token_url=token_url, client_id=client_id, client_secret=client_secret, account_urn=account_urn)
    headers = {"Authorization": f"Bearer {token}"}

    docs = list_new_dashboards(env_url=env_url, headers=headers)
    print(f"Found {len(docs)} new dashboards")

    outdir = pathlib.Path("dashboards_export_new")
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "index.json").write_text(json.dumps(docs, indent=2), encoding="utf-8")

    include_name = os.getenv("DT_NAME_IN_FILENAME", "0") == "1"
    for d in docs:
        did = d.get("id") or d.get("documentId") or d.get("document_id")
        if not did:
            print("Skipping item without id:", d); continue
        detail = get_document(env_url=env_url, doc_id=did, headers=headers)
        if include_name:
            nm = d.get("name") or d.get("title") or detail.get("title") or detail.get("name") or ""
            fname = f"{sanitize_filename(nm)}__{did}.json" if nm else f"{did}.json"
        else:
            fname = f"{did}.json"
        (outdir / fname).write_text(json.dumps(detail, indent=2), encoding="utf-8")
        print(f"Saved {fname}")

    print(f"✅ Done. Files in {outdir.resolve()}")

if __name__ == "__main__":
    main()
