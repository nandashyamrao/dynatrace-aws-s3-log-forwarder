
# Dynatrace Dashboard → Markdown Extractor

This script reads a Dynatrace dashboard JSON export and writes a **beautiful Markdown** document grouping each tile's Description and DQL/metric queries into fenced code blocks.

---

## Features
- Handles nested / double-escaped JSON.
- Supports common query key names: `query`, `dql`, `ql`, `metricSelector`, `metricExpression(s)`.
- Deduplicates queries per tile.
- Tiles without names are labelled **Dashboard Spacer Cell**.
- Adds syntax highlighting (`dql`) for Dynatrace Query Language.

---

## Usage
```bash
python3 extract_dt_dashboard_to_markdown.py dashboard.json
# Produces: dashboard_queries.md

python3 extract_dt_dashboard_to_markdown.py dashboard.json output.md
```
---

## Python Script

```python
#!/usr/bin/env python3
"""
Dynatrace Dashboard → Markdown extractor
----------------------------------------
Reads a Dynatrace dashboard JSON export and writes a **beautiful Markdown**
document grouping each tile's Description and DQL/metric queries into
fenced code blocks.

Usage:
    python3 extract_dt_dashboard_to_markdown.py dashboard.json [output.md]

Notes:
- Handles nested / double-escaped JSON.
- If a tile has no display name, it will be titled **"Dashboard Spacer Cell"**.
- Tries common query key names: query, dql, ql, metricSelector, metricExpression(s).
"""
import sys, json, pathlib, datetime, re
from typing import Any, Dict, List, Union

Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

QUERY_KEYS = {
    "query", "dql", "ql",
    "metricSelector", "metricExpression", "metricExpressions",
    "metric"
}
DESC_KEYS = {"description", "tileDescription", "markdown", "notes"}
NAME_KEYS = {"name", "title", "customName", "displayName", "tileType"}

def try_json_decode(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    s = value.strip()
    if not (s.startswith("{") or s.startswith("[") or s.startswith('"')):
        return value
    for _ in range(4):
        try:
            decoded = json.loads(s)
        except Exception:
            return s
        if isinstance(decoded, str):
            s = decoded.strip()
            continue
        return decoded
    return s

def normalize_query_value(val: Any) -> List[str]:
    out: List[str] = []
    val = try_json_decode(val)

    if isinstance(val, str):
        out.append(val)
    elif isinstance(val, list):
        for item in val:
            out.extend(normalize_query_value(item))
    elif isinstance(val, dict):
        for k, v in val.items():
            kl = k.lower()
            if kl in QUERY_KEYS or kl in {"value", "expression"}:
                out.extend(normalize_query_value(v))
            if isinstance(v, dict) and "string" in v and kl in QUERY_KEYS:
                out.extend(normalize_query_value(v["string"]))
        for k in ("query", "dql", "ql"):
            if k in val and isinstance(val[k], (str, list, dict)):
                out.extend(normalize_query_value(val[k]))
    return [s for s in (q.strip() for q in out) if s]

def gather_tiles(node: Json, ctx: List[str], acc: List[Dict[str, Any]]):
    if isinstance(node, dict):
        display = None
        for nk in NAME_KEYS:
            if nk in node and isinstance(node[nk], str) and node[nk].strip():
                display = node[nk].strip()
                break

        descs: List[str] = []
        for dk in DESC_KEYS:
            if dk in node and isinstance(node[dk], str):
                d = node[dk].strip()
                if d:
                    descs.append(d)

        queries: List[str] = []
        for qk in QUERY_KEYS:
            if qk in node:
                queries.extend(normalize_query_value(node[qk]))
        if "queries" in node:
            queries.extend(normalize_query_value(node["queries"]))

        if queries:
            acc.append({
                "context": " / ".join(ctx),
                "name": display or "Dashboard Spacer Cell",
                "description": " | ".join(descs) if descs else "",
                "queries": unique_preserve(queries),
            })

        for k, v in node.items():
            gather_tiles(v, ctx + [k], acc)

    elif isinstance(node, list):
        for idx, item in enumerate(node):
            gather_tiles(item, ctx + [f"[{idx}]"], acc)

def unique_preserve(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def detect_code_lang(q: str) -> str:
    if re.search(r"\b(fetch|timeseries|fields|filter|lookup|make|join|summarize|parse|sort|limit)\b", q):
        return "dql"
    if any(tok in q for tok in [":", "splitBy(", "rate(", "timeshift("]) and "\n" not in q:
        return "text"
    return "text"

def md_escape_heading(s: str) -> str:
    return s.replace("#", "\#").strip()

def render_markdown(tiles: List[Dict[str, Any]], title: str) -> str:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    total_q = sum(len(t["queries"]) for t in tiles)
    md = []
    md.append(f"# {md_escape_heading(title)} — Extracted Queries\n")
    md.append(f"_Generated on {ts}. Tiles with queries: **{len(tiles)}**. Total queries: **{total_q}**._\n")
    md.append("\n---\n")
    md.append("## Table of contents\n")
    for i, t in enumerate(tiles, 1):
        anchor = re.sub(r'[^a-z0-9\- ]+', '', t["name"].lower()).replace(" ", "-")
        md.append(f"- [{t['name']}](#{anchor})")
    md.append("\n---\n")

    md.append("## Summary\n")
    md.append("| # | Tile | Queries | Has Description |\n|---:|---|---:|:--:|\n")
    for i, t in enumerate(tiles, 1):
        md.append(f"| {i} | {t['name']} | {len(t['queries'])} | {'✅' if t['description'] else '—'} |\n")
    md.append("\n---\n")

    for i, t in enumerate(tiles, 1):
        md.append(f"## {t['name']}\n")
        md.append(f"**Context:** `{t['context']}`\n\n")
        if t["description"]:
            md.append("> " + t["description"].replace("\n", "\n> ") + "\n\n")
        for qi, q in enumerate(t["queries"], 1):
            lang = detect_code_lang(q)
            md.append(f"**Query {qi}**\n")
            md.append(f"```{lang}\n{q}\n```\n\n")
        md.append("---\n")
    return "".join(md)

def main():
    if len(sys.argv) < 2:
        print("Usage: extract_dt_dashboard_to_markdown.py <dashboard.json> [output.md]", file=sys.stderr)
        sys.exit(1)

    in_path = pathlib.Path(sys.argv[1])
    out_path = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(in_path.stem + "_queries.md")

    with in_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    tiles: List[Dict[str, Any]] = []
    gather_tiles(data, ctx=["root"], acc=tiles)

    title = (data.get("dashboardMetadata", {}) or {}).get("name") or in_path.stem
    md = render_markdown(tiles, title)

    out_path.write_text(md, encoding="utf-8")
    print(f"Wrote Markdown with {len(tiles)} tiles → {out_path}")

if __name__ == "__main__":
    main()
```
