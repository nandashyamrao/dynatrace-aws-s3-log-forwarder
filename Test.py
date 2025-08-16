#!/usr/bin/env python3
import os
import requests
import json
from pathlib import Path

# Load values from environment
CLIENT_ID = os.getenv("DT_CLIENT_ID")
CLIENT_SECRET = os.getenv("DT_CLIENT_SECRET")
ACCOUNT_URN = os.getenv("DT_ACCOUNT_URN")
ENV_URL = os.getenv("DT_ENV_URL")  # e.g. https://xxxx.live.dynatrace.com

if not all([CLIENT_ID, CLIENT_SECRET, ACCOUNT_URN, ENV_URL]):
    raise RuntimeError("Missing one of DT_CLIENT_ID, DT_CLIENT_SECRET, DT_ACCOUNT_URN, DT_ENV_URL")

TOKEN_URL = "https://sso.dynatrace.com/sso/oauth2/token"

def get_token():
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "resource": ACCOUNT_URN,
    }
    resp = requests.post(TOKEN_URL, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]

def get_dashboards(token):
    url = f"{ENV_URL}/api/config/v1/dashboards"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json().get("dashboards", [])

def get_dashboard(token, dashboard_id):
    url = f"{ENV_URL}/api/config/v1/dashboards/{dashboard_id}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def main():
    token = get_token()
    dashboards = get_dashboards(token)

    out_dir = Path("dashboards")
    out_dir.mkdir(exist_ok=True)

    print(f"Found {len(dashboards)} dashboards")

    for d in dashboards:
        dash_id = d["id"]
        dash_name = d["name"].replace(" ", "_").replace("/", "_")
        details = get_dashboard(token, dash_id)
        out_path = out_dir / f"{dash_name}_{dash_id}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(details, f, indent=2)
        print(f"Saved {out_path}")

if __name__ == "__main__":
    main()
