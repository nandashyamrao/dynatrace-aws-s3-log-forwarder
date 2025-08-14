
# Dynatrace Dashboard -> Markdown Extractor (Organized Output, Collapsible Sections)

This upgraded extractor produces a **clean, navigable** Markdown with:
- **Named tiles first**, then spacer cells.
- A **Summary table** with a 1-line preview of each query.
- **Collapsible** tile sections (`<details>`/`<summary>`) to keep the page short.
- A **Variables** section (auto-detected `$variables` referenced in queries).
- Optional **Tile Type** (when available) shown next to the title.
- Syntax-highlighted code blocks for DQL.

---

## Usage
```bash
python3 extract_dt_dashboard_to_markdown_v2.py dashboard.json
# -> dashboard_queries.md

# Or specify output
python3 extract_dt_dashboard_to_markdown_v2.py dashboard.json cloudfront_queries.md
```
---

## Python Script (v2)

```python
#!/usr/bin/env python3
"""
Dynatrace Dashboard -> Markdown extractor (v2, organized + collapsible)
---------------------------------------------------------------------
- Groups named tiles first, then spacer cells
- Collapsible sections per tile
- Summary table with first-line preview
- Auto-detects $variables used in queries
"""
import sys, json, pathlib, datetime, re, html
from typing import Any, Dict, List, Tuple, Union

Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

QUERY_KEYS = {
    "query", "dql", "ql",
    "metricSelector", "metricExpression", "metricExpressions",
    "metric"
}
DESC_KEYS = {"description", "tileDescription", "markdown", "notes"}
NAME_KEYS = {"name", "title", "customName", "displayName"}
TYPE_KEYS = {"tileType", "type"}

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

def unique(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def gather_tiles(node: Json, ctx: List[str], acc: List[Dict[str, Any]]):
    if isinstance(node, dict):
        display = None
        for nk in NAME_KEYS:
            if nk in node and isinstance(node[nk], str) and node[nk].strip():
                display = node[nk].strip()
                break

        tile_type = None
        for tk in TYPE_KEYS:
            if tk in node and isinstance(node[tk], str) and node[tk].strip():
                tile_type = node[tk].strip()
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
                "type": tile_type or "—",
                "description": " | ".join(descs) if descs else "",
                "queries": unique(queries),
            })

        for k, v in node.items():
            gather_tiles(v, ctx + [k], acc)

    elif isinstance(node, list):
        for idx, item in enumerate(node):
            gather_tiles(item, ctx + [f"[{idx}]"], acc)

def detect_code_lang(q: str) -> str:
    if re.search(r"\b(fetch|timeseries|fields|filter|lookup|make|join|summarize|parse|sort|limit)\b", q):
        return "dql"
    if any(tok in q for tok in [":", "splitBy(", "rate(", "timeshift("]) and "\n" not in q:
        return "text"
    return "text"

def first_line(s: str, maxlen: int = 96) -> str:
    fl = s.splitlines()[0].strip()
    return (fl[:maxlen] + "…") if len(fl) > maxlen else fl

def collect_variables(tiles: List[Dict[str, Any]]) -> List[str]:
    vars_found = []
    for t in tiles:
        for q in t["queries"]:
            vars_found += re.findall(r"\$[A-Za-z_][A-Za-z0-9_]*", q)
    return unique(vars_found)

def render_markdown(tiles: List[Dict[str, Any]], title: str) -> str:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    total_q = sum(len(t["queries"]) for t in tiles)

    tiles_sorted = sorted(tiles, key=lambda t: (t["name"] == "Dashboard Spacer Cell", t["name"].lower()))
    variables = collect_variables(tiles_sorted)

    md = []
    md.append(f"# {title} — Extracted Queries\n\n")
    md.append(f"_Generated on {ts}. Tiles with queries: **{len(tiles_sorted)}**. Total queries: **{total_q}**._\n\n")
    if variables:
        md.append(f"**Detected dashboard variables:** {' '.join(f'`{v}`' for v in variables)}\n\n")
    md.append("---\n\n")

    md.append("## Table of contents\n")
    toc_items = [f"[{t['name']}](" + '#' + re.sub(r'[^a-z0-9\- ]+', '', t['name'].lower()).replace(' ', '-') + ")" for t in tiles_sorted]
    md.append(", ".join(toc_items) + "\n\n---\n\n")

    md.append("## Summary\n")
    md.append("| # | Tile | Type | Queries | Preview |\n|---:|---|---|---:|---|\n")
    for i, t in enumerate(tiles_sorted, 1):
        preview = first_line(t["queries"][0]) if t["queries"] else ""
        md.append(f"| {i} | {t['name']} | {t['type']} | {len(t['queries'])} | `{preview}` |\n")
    md.append("\n---\n\n")

    for i, t in enumerate(tiles_sorted, 1):
        anchor = re.sub(r'[^a-z0-9\- ]+', '', t["name"].lower()).replace(' ', '-')
        md.append(f"## {t['name']}\n\n")
        md.append(f"**Type:** `{t['type']}`  \n")
        md.append(f"**Context:** `{t['context']}`\n\n")
        if t["description"]:
            md.append("> " + t["description"].replace("\n", "\n> ") + "\n\n")
        for qi, q in enumerate(t["queries"], 1):
            lang = detect_code_lang(q)
            lines = len(q.splitlines())
            md.append(f"<details>\n<summary><strong>Query {qi}</strong> — {lines} line{'s' if lines!=1 else ''}</summary>\n\n")
            md.append(f"\n```{lang}\n{q}\n```\n")
            md.append("\n</details>\n\n")
        md.append("---\n\n")
    return "".join(md)

def main():
    if len(sys.argv) < 2:
        print("Usage: extract_dt_dashboard_to_markdown_v2.py <dashboard.json> [output.md]", file=sys.stderr)
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
    print(f"Wrote Markdown with {len(tiles)} tiles -> {out_path}")

if __name__ == "__main__":
    main()
```
