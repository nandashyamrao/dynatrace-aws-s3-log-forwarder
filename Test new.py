#!/usr/bin/env python3
import os, sys, json, time, pathlib, argparse, textwrap
from typing import Optional, Dict, Any, List
import requests

DOTFILE = pathlib.Path.home() / ".dynatraceoauth"

def read_dotfile() -> Dict[str, str]:
    if not DOTFILE.exists(): return {}
    m = {}
    for line in DOTFILE.read_text(encoding="utf-8").splitlines():
        if ":" in line:
            k,v = line.split(":",1)
            m[k.strip()] = v.strip()
    return m

def env_or_dot(env: str, key: str, default: Optional[str]=None) -> Optional[str]:
    return os.environ.get(env) or read_dotfile().get(key, default)

def pick_cert_verify():
    cab = os.environ.get("REQUESTS_CA_BUNDLE")
    if cab and pathlib.Path(cab).exists():
        return cab
    dtcab = os.environ.get("DT_CA_BUNDLE")
    if dtcab:
        p = pathlib.Path(dtcab)
        if p.is_file():
            return str(p)
        if p.is_dir():
            pref = p / "cacerts.crt"
            if pref.exists(): return str(pref)
            for c in p.iterdir():
                if c.suffix.lower() in (".crt",".pem") and c.is_file():
                    return str(c)
    home = pathlib.Path.home() / "sfacacerts" / "cacerts.crt"
    if home.exists(): return str(home)
    return True  # system

def post_token(url: str, data: Dict[str,str], verify, timeout=30) -> requests.Response:
    return requests.post(url, data=data, timeout=timeout, verify=verify)

def pretty_json(obj) -> str:
    try: return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception: return str(obj)

def explain_failure(resp: requests.Response, token_url: str, tried: Dict[str,str], scopes: str):
    body_text = resp.text
    try:
        body = resp.json()
    except Exception:
        body = {"raw": body_text}

    err = (body if isinstance(body, dict) else {}).get("error", "")
    desc = (body if isinstance(body, dict) else {}).get("error_description", "")
    issued = (body if isinstance(body, dict) else {}).get("issued", "")

    print("\n❌ Token request failed")
    print(f"   HTTP {resp.status_code} at {token_url}\n")
    print("Response body:")
    print(textwrap.indent(pretty_json(body), "  "))
    print("\nParameters used:")
    print(textwrap.indent(pretty_json(tried), "  "))
    print(f"\nScopes used: {scopes or '(none)'}")

    # Dormant/invalid client detection (what your screenshot shows)
    # Dynatrace often returns error=invalid_request + 'issued' or similar.
    if "invalid_client" in err or "invalid_client" in desc:
        print("\n🔎 Diagnosis: The OAuth client ID/secret is invalid.")
        print("   → Re-check DT_CLIENT_ID/DT_CLIENT_SECRET, or recreate the client.")
    elif "invalid_request" in err or "invalid_request" in desc or issued:
        print("\n🔎 Diagnosis: The OAuth client may be **dormant/disabled** or the account mapping is invalid.")
        print("   → Ask a Dynatrace admin to create/enable a new OAuth client (Accounts > Identity & access > OAuth clients).")
    elif "unauthorized_client" in err:
        print("\n🔎 Diagnosis: Client lacks permission for this grant/resource/audience.")
        print("   → Verify the client has the required scopes/permissions.")
    elif "access_denied" in err:
        print("\n🔎 Diagnosis: The authorization server denied the request.")
        print("   → Check scopes/audience and client configuration.")
    elif resp.status_code == 400:
        print("\n🔎 Diagnosis: Bad request (400). Often caused by wrong token URL, resource, audience, or scopes.")

    # Provide a copy/paste curl to reproduce exactly
    curl_lines = [
        f"curl -sS {token_url!r} \\",
        "  -H 'Content-Type: application/x-www-form-urlencoded' \\",
        "  --data-urlencode 'grant_type=client_credentials' \\",
        f"  --data-urlencode 'client_id={tried.get('client_id','')}' \\",
        f"  --data-urlencode 'client_secret={tried.get('client_secret','')}' \\"
    ]
    if tried.get("resource"): curl_lines.append(f"  --data-urlencode 'resource={tried.get('resource')}' \\")
    if tried.get("audience"): curl_lines.append(f"  --data-urlencode 'audience={tried.get('audience')}' \\")
    if scopes: curl_lines.append(f"  --data-urlencode 'scope={scopes}'")
    print("\nReproduce with curl:")
    print(textwrap.indent("\n".join(curl_lines), "  "))
    print()

def try_token_flows(token_url: str, env_url: str, client_id: str, client_secret: str,
                    account_urn: Optional[str], scopes: str, verify) -> Optional[str]:
    """
    Try multiple safe combinations that work across tenants:
    1) resource=account_urn, audience=account_urn
    2) resource=env_url
    3) no resource/audience
    """
    attempts: List[Dict[str,str]] = []

    if account_urn:
        attempts.append({
            "grant_type":"client_credentials",
            "client_id":client_id,
            "client_secret":client_secret,
            "resource":account_urn,
            "audience":account_urn,
            "scope":scopes
        })

    attempts.append({
        "grant_type":"client_credentials",
        "client_id":client_id,
        "client_secret":client_secret,
        "resource":env_url,
        "scope":scopes
    })

    attempts.append({
        "grant_type":"client_credentials",
        "client_id":client_id,
        "client_secret":client_secret,
        "scope":scopes
    })

    for data in attempts:
        resp = post_token(token_url, data, verify=verify)
        try:
            resp.raise_for_status()
            tok = resp.json().get("access_token")
            if tok:
                return tok
        except requests.HTTPError:
            explain_failure(resp, token_url, {k:v for k,v in data.items() if k!='client_secret'}, scopes)
    return None

def main():
    ap = argparse.ArgumentParser(description="Dynatrace OAuth token doctor")
    ap.add_argument("--print", dest="print_only", action="store_true", help="Print token to stdout if successful")
    args = ap.parse_args()

    client_id = env_or_dot("DT_CLIENT_ID", "client_id")
    client_secret = env_or_dot("DT_CLIENT_SECRET", "client_secret")
    env_url = env_or_dot("DT_ENV_URL", "env_url")
    account_urn = env_or_dot("DT_ACCOUNT_URN", "account_urn")
    token_url = env_or_dot("DT_SSO_URL", "sso_url") or "https://sso.dynatrace.com/sso/oauth2/token"
    scopes = os.environ.get("DT_SCOPES", "dynatrace.environment.read app-engine:apps:read")

    missing = [n for n,v in [("DT_CLIENT_ID",client_id),("DT_CLIENT_SECRET",client_secret),("DT_ENV_URL",env_url)] if not v]
    if missing:
        sys.exit("Missing: " + ", ".join(missing) + " (set env vars or ~/.dynatraceoauth)")

    verify = pick_cert_verify()
    tok = try_token_flows(token_url, env_url, client_id, client_secret, account_urn, scopes, verify)
    if not tok:
        sys.exit(1)

    print("✅ Token acquired.")
    if args.print_only:
        print(tok)

if __name__ == "__main__":
    main()
