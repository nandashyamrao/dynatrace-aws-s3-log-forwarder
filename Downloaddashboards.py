#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynatrace NEW Dashboards Export via OAuth2 (client credentials)
- Uses Platform Document Service: /platform/document/v1/documents
- Lists documents with filter type='dashboard' (new dashboards)
- Downloads each dashboard document JSON to ./dashboards_export_new/<id>.json
...
"""
import os, json, pathlib, typing as t, requests
from urllib.parse import urljoin

TOKEN_URL_DEFAULT = "https://sso.dynatrace.com/sso/oauth2/token"

def getenv_req(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise SystemExit(f"Missing required environment variable: {name}")
    return v

def get_tls_kwargs() -> dict:
    tls: dict = {}
    ca = os.getenv("DT_CA_BUNDLE") or os.getenv("REQUESTS_CA_BUNDLE")
    if ca:
        tls["verify"] = ca
    cert = os.getenv("DT_CLIENT_CERT")
    key  = os.getenv("DT_CLIENT_KEY")
    if cert and key:
        tls["cert"] = (cert, key)
    elif cert:
        tls["cert"] = cert
    return tls

def request_token(*, token_url: str, client_id: str, client_secret: str, account_urn: str) -> str:
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "resource": account_urn,
    }
    r = requests.post(token_url, data=data, timeout=30, **get_tls_kwargs())
    r.raise_for_status()
    js = r.json()
    token = js.get("access_token")
    if not token:
        raise SystemExit(f"No access_token in token response: {js}")
    return token

def list_new_dashboards(*, env_url: str, headers: dict) -> t.List[dict]:
    base = env_url.rstrip('/') + '/'
    url = urljoin(base, "platform/document/v1/documents")
    params = {"filter": "type='dashboard'"}
    all_docs: t.List[dict] = []
    tls = get_tls_kwargs()

    while True:
        r = requests.get(url, headers=headers, params=params, timeout=30, **tls)
        r.raise_for_status()
        data = r.json()
        items = data.get("items") or data.get("documents") or data.get("results") or data.get("entities") or []
        if isinstance(items, list):
            all_docs.extend(items)
        next_key = data.get("nextPageKey") or data.get("next_page_key") or data.get("nextToken")
        if not next_key:
            break
        params["nextPageKey"] = next_key
    return all_docs

def get_document(*, env_url: str, doc_id: str, headers: dict) -> dict:
    base = env_url.rstrip('/') + '/'
    url = urljoin(base, f"platform/document/v1/documents/{doc_id}")
    r = requests.get(url, headers=headers, timeout=30, **get_tls_kwargs())
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
    account_urn   = getenv_req("DT_ACCOUNT_URN")
    token_url     = os.getenv("DT_OAUTH_TOKEN_URL", TOKEN_URL_DEFAULT).strip()

    token = request_token(token_url=token_url, client_id=client_id, client_secret=client_secret, account_urn=account_urn)
    headers = {"Authorization": f"Bearer {token}"}

    docs = list_new_dashboards(env_url=env_url, headers=headers)
    print(f"Found {len(docs)} new dashboards")

    outdir = pathlib.Path("dashboards_export_new")
    outdir.mkdir(parents=True, exist_ok=True)

    (outdir / "index.json").write_text(json.dumps(docs, indent=2), encoding="utf-8")

    for d in docs:
        did = d.get("id") or d.get("documentId") or d.get("document_id")
        dname = d.get("name") or d.get("title") or ""
        if not did:
            print("Skipping item without id:", d); continue
        doc = get_document(env_url=env_url, doc_id=did, headers=headers)
        fname = f"{did}.json"
        (outdir / fname).write_text(json.dumps(doc, indent=2), encoding="utf-8")
        print(f"Saved {dname or did} -> {fname}")

    print(f"✅ Done. Files in {outdir.resolve()}")

if __name__ == "__main__":
    main()
