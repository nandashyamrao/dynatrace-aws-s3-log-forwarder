#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dynatrace Dashboard -> Markdown extractor
- Reads all *.json dashboards in the current directory
- Looks up human-friendly name/owner from dashboards.csv (id,name,owner)
- Builds a direct link to the dashboard using DT_ENV_URL
- Writes <dashboard-name>_TileQueries.md with Overview

Env:
  DT_ENV_URL=https://<tenant>.live.dynatrace.com  (required for links)

CSV:
  dashboards.csv with columns: id,name,owner   (header order doesn’t matter)

"""

import os, re, csv, json, pathlib, datetime

HERE = pathlib.Path(".").resolve()
CSV_FILE = HERE / "dashboards.csv"
DT_ENV_URL = os.environ.get("DT_ENV_URL", "").rstrip("/")
NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# -------- robust CSV loader (handles BOM/Windows encodings) --------
def open_csv_robust(path: pathlib.Path):
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return path.open("r", encoding=enc, newline="")
        except UnicodeDecodeError:
            continue
    return path.open("r", encoding="utf-8", errors="replace", newline="")

def load_index(csv_path: pathlib.Path):
    idx = {}
    if not csv_path.exists():
        return idx
    with open_csv_robust(csv_path) as f:
        # Dialect sniff with safe fallback
        sample = f.read(4096); f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        # Normalize header keys
        reader.fieldnames = [ (h or "").strip().lower() for h in (reader.fieldnames or []) ]
        for row in reader:
            rid = (row.get("id") or "").strip().lower()
            if not rid:
                continue
            name = (row.get("name") or "").strip()
            owner = (row.get("owner") or "").strip()
            url = (row.get("url") or "").strip()  # optional column; if present we’ll use it
            idx[rid] = {"name": name, "owner": owner, "url": url}
    return idx

INDEX = load_index(CSV_FILE)

def normalize_id(s: str) -> str:
    return (s or "").strip().lower()

def dql_preview_from_tile(tile: dict) -> str:
    # very light preview: first non-empty query-like string we find
    candidates = []
    for k in ("query", "dql", "ql", "metricSelector", "metricExpression", "metric"):
        v = tile.get(k)
        if isinstance(v, str) and v.strip():
            candidates.append(v.strip())
    if candidates:
        return candidates[0].splitlines()[0][:120]
    return ""

def find_queries(tile: dict):
    out = []
    def walk(x):
        if isinstance(x, dict):
            for k,v in x.items():
                if k in ("query","dql","ql","metricSelector","metricExpression","metric") and isinstance(v,str):
                    if v.strip():
                        out.append(v.strip())
                walk(v)
        elif isinstance(x, list):
            for it in x:
                walk(it)
    walk(tile)
    # de-dup, keep order
    seen=set(); uniq=[]
    for q in out:
        if q not in seen:
            seen.add(q); uniq.append(q)
    return uniq

def gather_tiles(data: dict):
    tiles = []
    def walk(n, ctx):
        if isinstance(n, dict):
            if any(k in n for k in ("query","dql","ql","metricSelector","metricExpression","metric","queries")):
                name = n.get("name") or n.get("title") or n.get("customName") or n.get("displayName") or "—"
                ttype = n.get("tileType") or n.get("type") or "—"
                viz = (n.get("visualConfig",{}) or {}).get("type") or n.get("visualization") or "—"
                qs = find_queries(n)
                tiles.append({
                    "name": str(name),
                    "type": str(ttype),
                    "visualization": str(viz),
                    "queries": qs,
                    "preview": dql_preview_from_tile(n),
                })
            for v in n.values():
                walk(v, ctx)
        elif isinstance(n, list):
            for it in n:
                walk(it, ctx)
    walk(data, ["root"])
    return tiles

def build_url(dash_id: str) -> str:
    meta = INDEX.get(normalize_id(dash_id), {})
    if meta.get("url"):
        return meta["url"]
    if DT_ENV_URL:
        return f"{DT_ENV_URL}/ui/apps/dynatrace.dashboards/dashboard/{dash_id}"
    return ""  # no env URL

def render_md(dash_id: str, data: dict, out_path: pathlib.Path):
    # Prefer CSV name/owner; fall back to JSON metadata
    meta = INDEX.get(normalize_id(dash_id), {})
    csv_name = meta.get("name") or ""
    json_name = (data.get("dashboardMetadata", {}) or {}).get("name") or ""
    name = csv_name or json_name or dash_id
    owner = meta.get("owner") or (data.get("dashboardMetadata", {}) or {}).get("owner") or "—"
    link = build_url(dash_id)

    tiles = gather_tiles(data)
    total_q = sum(len(t["queries"]) for t in tiles)

    md = []
    md.append(f"# {name} — Tile Query Details\n\n")
    md.append(f"**Dashboard:** {f'[{dash_id}]({link})' if link else dash_id}  \n")
    md.append(f"**Owner:** {owner}\n\n")
    md.append(f"_Generated on {NOW}. Tiles with queries: **{len(tiles)}**. Total queries: **{total_q}**._\n\n")

    # Overview table
    md.append("## Overview\n\n")
    md.append("| # | Title | Type | Visualization | Queries | Preview |\n")
    md.append("|---:|---|---|---|---:|---|\n")
    for i, t in enumerate(tiles, 1):
        preview = f"`{t['preview']}`" if t["preview"] else "—"
        md.append(f"| {i} | {t['name']} | {t['type']} | {t['visualization']} | {len(t['queries'])} | {preview} |\n")
    md.append("\n")

    out_path.write_text("".join(md), encoding="utf-8")
    print(f"Wrote {out_path.name}")

def main():
    json_files = sorted(HERE.glob("*.json"))
    if not json_files:
        print("No JSON files found in current folder.")
        return
    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            # try tolerant read
            data = json.loads(jf.read_text(encoding="utf-8", errors="replace"))
        dash_id = data.get("id") or jf.stem
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", (INDEX.get(normalize_id(dash_id), {}).get("name") or dash_id))
        out_md = jf.with_name(f"{safe_name}_TileQueries.md")
        render_md(dash_id, data, out_md)

if __name__ == "__main__":
    main()
