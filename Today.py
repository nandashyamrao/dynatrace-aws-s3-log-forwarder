#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build Markdown files from downloaded Dynatrace dashboard JSONs.

Inputs:
  - dashboards.csv   (columns: id,name,owner)
  - dashboards_json/ (JSON files named <id>.json downloaded by the shell script)
Environment:
  - DT_ENV_URL       (e.g. https://cf94088.apps.dynatrace.com)

Output:
  - dashboards_md/<name>_TileQueries.md (each includes link, name, owner)
"""

import os, csv, json, re, sys
from pathlib import Path
from datetime import datetime

DT_ENV_URL = os.environ.get("DT_ENV_URL", "").rstrip("/")
if not DT_ENV_URL:
    sys.exit("Please export DT_ENV_URL (e.g. https://<tenant>.apps.dynatrace.com)")

CSV_FILE = Path("dashboards.csv")
JSON_DIR = Path("dashboards_json")
OUT_DIR = Path("dashboards_md")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def slugify(name: str) -> str:
    s = name.strip()
    s = re.sub(r"[^\w\-.]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_")

# Load id -> (name, owner)
id_to_meta = {}
with CSV_FILE.open(newline="", encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        id_ = (row.get("id") or "").strip()
        name = (row.get("name") or "").strip()
        owner = (row.get("owner") or "").strip()
        if id_:
            id_to_meta[id_] = (name or id_, owner or "—")

def first_line(s: str, maxlen=96) -> str:
    fl = (s or "").splitlines()[0].strip()
    return (fl[:maxlen] + "…") if len(fl) > maxlen else fl

def gather_tiles(d: dict):
    """Return a list of {name,type,visualization,queries} tiles if present."""
    tiles = []
    for t in d.get("tiles", []):
        name = t.get("name") or t.get("title") or "Tile"
        ttype = t.get("tileType") or t.get("type") or "—"
        vis = t.get("visualization") or (t.get("visualConfig", {}) or {}).get("type") or "—"
        queries = []
        # Dynatrace exports can store queries in different keys; lightly search common spots
        for key in ("query","queries","dql","ql","metricExpression","metricSelector"):
            v = t.get(key)
            if isinstance(v, str) and v.strip():
                queries.append(v.strip())
            elif isinstance(v, list):
                for it in v:
                    if isinstance(it, str) and it.strip():
                        queries.append(it.strip())
        tiles.append({
            "name": name,
            "type": ttype,
            "visualization": vis,
            "queries": queries or []
        })
    return tiles

def build_markdown_for(id_: str, name: str, owner: str, data: dict):
    # Dashboard URL for hyperlink
    dash_url = f"{DT_ENV_URL}/ui/apps/dynatrace.dashboards/dashboard/{id_}"

    # Filename
    safe = slugify(f"{name}_TileQueries") + ".md"
    out_path = OUT_DIR / safe

    tiles = gather_tiles(data)
    total_q = sum(len(t["queries"]) for t in tiles)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = []
    md.append(f"# {name} — Tile Query Details\n\n")
    md.append(f"**Dashboard:** [{name}]({dash_url})  \n")
    md.append(f"**Owner:** `{owner}`  \n")
    md.append(f"**Dashboard ID:** `{id_}`\n\n")
    md.append(f"_Generated on {ts}. Tiles with queries: **{len(tiles)}**. Total queries: **{total_q}**._\n\n")
    md.append("---\n\n")

    # Overview table
    md.append("## Overview\n\n")
    md.append("| # | Title | Type | Visualization | Queries | Preview |\n")
    md.append("|---:|---|---|---|---:|---|\n")
    for i,t in enumerate(tiles,1):
        preview = first_line(t["queries"][0]) if t["queries"] else ""
        md.append(f"| {i} | {t['name']} | {t['type']} | {t['visualization']} | {len(t['queries'])} | `{preview}` |\n")
    md.append("\n")

    out_path.write_text("".join(md), encoding="utf-8")
    print(f"✓ {out_path}")
    return out_path

def main():
    if not JSON_DIR.exists():
        sys.exit(f"JSON directory not found: {JSON_DIR}")

    made = 0
    for jf in JSON_DIR.glob("*.json"):
        id_ = jf.stem
        meta = id_to_meta.get(id_)
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"✗ Skip {jf.name}: {e}")
            continue

        if meta:
            name, owner = meta
        else:
            name = data.get("name") or id_
            owner = "—"

        build_markdown_for(id_, name, owner, data)
        made += 1
    print(f"\nDone. Wrote {made} Markdown files to {OUT_DIR}/")

if __name__ == "__main__":
    main()
