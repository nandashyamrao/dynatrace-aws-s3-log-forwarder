
# Dynatrace Dashboard -> Markdown Extractor (v5: Variables Section + Usage Map)

This version adds a **Variables** section at the top that shows each variable’s **DQL** and **which tiles use it** (with links).  
The overview table now includes a **Vars Used** column listing variables referenced by each tile.

---

## Usage
```bash
python3 extract_dt_dashboard_to_markdown_v5.py dashboard.json
# -> dashboard_queries.md
```

---

## Python Script (v5)

```python
#!/usr/bin/env python3
"""
Dynatrace Dashboard -> Markdown extractor (v5)
- Variables section at top with each variable's DQL + tile usage (links)
- Overview table includes "Vars Used"
- Keeps: Visualization column, named-first ordering, collapsible queries
"""
import sys, json, pathlib, datetime, re
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

def get_nested(d: Dict[str, Any], path: List[str]):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur

def detect_visualization(node: Dict[str, Any]) -> str:
    candidates = []
    v = get_nested(node, ["visualConfig", "type"])
    if isinstance(v, str) and v.strip():
        candidates.append(v.strip())
    for k in ("visualization", "viz", "chartType", "graphType"):
        vv = node.get(k)
        if isinstance(vv, str) and vv.strip():
            candidates.append(vv.strip())
    if not candidates and "visualConfig" in node and isinstance(node["visualConfig"], dict):
        for k, vv in node["visualConfig"].items():
            if isinstance(vv, str) and vv.strip() and k.lower() in ("visualization", "type", "charttype", "graphtype"):
                candidates.append(vv.strip())
    return candidates[0] if candidates else "—"

def gather_tiles(node, ctx, acc):
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

        descs = []
        for dk in DESC_KEYS:
            if dk in node and isinstance(node[dk], str):
                d = node[dk].strip()
                if d:
                    descs.append(d)

        queries = []
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
                "visualization": detect_visualization(node),
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

# -------- Variables parsing & usage mapping --------

def parse_variables(data: Dict[str, Any]) -> Dict[str, str]:
    """Return {var_name -> dql_string} from dashboard JSON."""
    var_map: Dict[str, str] = {}
    vars_section = data.get("variables") or data.get("dashboardMetadata", {}).get("variables")
    if isinstance(vars_section, list):
        for v in vars_section:
            if not isinstance(v, dict):
                continue
            name = v.get("name") or v.get("key") or v.get("id")
            if not isinstance(name, str) or not name.strip():
                continue
            # Try common locations for the DQL/definition
            dql = None
            # direct fields
            for k in ("query", "dql", "definition", "data"):
                val = v.get(k)
                if isinstance(val, str) and val.strip():
                    dql = val.strip()
                    break
                if isinstance(val, dict):
                    # nested
                    for kk in ("query", "dql", "data", "string"):
                        vv = val.get(kk)
                        if isinstance(vv, str) and vv.strip():
                            dql = vv.strip()
                            break
                    if dql:
                        break
            if dql is None:
                # Any other nested string that looks like DQL
                for vv in v.values():
                    if isinstance(vv, str) and ("fetch " in vv or "summarize" in vv or "filter" in vv):
                        dql = vv.strip()
                        break
            if dql:
                var_map[name.strip()] = dql
    return var_map

def find_vars_in_query(q: str, var_names: List[str]) -> List[str]:
    found = []
    for vn in var_names:
        # Match $var or ${var}
        pattern = rf"(\$\{{{re.escape(vn)}\}}|\${re.escape(vn)}\b)"
        if re.search(pattern, q):
            found.append(vn)
    return unique(found)

def build_var_usage(tiles: List[Dict[str, Any]], var_map: Dict[str, str]) -> Dict[str, List[str]]:
    """Return {var_name -> [tile_names_using_it]}"""
    usage = {vn: [] for vn in var_map.keys()}
    for t in tiles:
        used = set()
        for q in t["queries"]:
            for vn in var_map.keys():
                if re.search(rf"(\$\{{{re.escape(vn)}\}}|\${re.escape(vn)}\b)", q):
                    used.add(vn)
        for vn in used:
            usage[vn].append(t["name"])
        t["vars_used"] = sorted(list(used))
    return usage

def anchor_for(name: str) -> str:
    return re.sub(r'[^a-z0-9\- ]+', '', name.lower()).replace(' ', '-')

def render_markdown(tiles, title: str, var_map: Dict[str, str]) -> str:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    total_q = sum(len(t["queries"]) for t in tiles)

    tiles_sorted = sorted(tiles, key=lambda t: (t["name"] == "Dashboard Spacer Cell", t["name"].lower()))
    # Build variable usage
    usage = build_var_usage(tiles_sorted, var_map)

    md = []
    md.append(f"# {title} — Extracted Queries\n\n")
    md.append(f"_Generated on {ts}. Tiles with queries: **{len(tiles_sorted)}**. Total queries: **{total_q}**._\n\n")
    if var_map:
        md.append(f"**Detected dashboard variables:** {' '.join(f'`{v}`' for v in var_map.keys())}\n\n")
    md.append("---\n\n")

    # Variables Section
    if var_map:
        md.append("## Variables\n")
        for vn, vdql in var_map.items():
            md.append(f"### `{vn}`\n\n")
            # Link to tiles that use it
            tiles_for_var = usage.get(vn, [])
            if tiles_for_var:
                links = ", ".join(f"[{t}](" + "#" + anchor_for(t) + ")" for t in tiles_for_var)
                md.append(f"Used in: {links}\n\n")
            md.append("```dql\n" + vdql + "\n```\n\n")
        md.append("---\n\n")

    # Overview table (with Vars Used)
    md.append("## Overview\n")
    md.append("| # | Tile | Type | Visualization | Vars Used | Queries | Preview |\n|---:|---|---|---|---|---:|---|\n")
    for i, t in enumerate(tiles_sorted, 1):
        link = f"[{t['name']}](" + "#" + anchor_for(t['name']) + ")"
        preview = first_line(t["queries"][0]) if t["queries"] else ""
        vars_list = " ".join(f"`{v}`" for v in t.get("vars_used", [])) or "—"
        md.append(f"| {i} | {link} | {t['type']} | {t['visualization']} | {vars_list} | {len(t['queries'])} | `{preview}` |\n")
    md.append("\n---\n\n")

    # Detail sections
    for i, t in enumerate(tiles_sorted, 1):
        md.append(f"## {t['name']}\n\n")
        md.append(f"**Type:** `{t['type']}`  \\n")
        md.append(f"**Visualization:** `{t['visualization']}`  \\n")
        md.append(f"**Context:** `{t['context']}`\n\n")
        if t.get("vars_used"):
            md.append("**Vars Used:** " + ", ".join(f"`{v}`" for v in t["vars_used"]) + "\n\n")
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
        print("Usage: extract_dt_dashboard_to_markdown_v5.py <dashboard.json> [output.md]", file=sys.stderr)
        sys.exit(1)

    in_path = pathlib.Path(sys.argv[1])
    out_path = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(in_path.stem + "_queries.md")

    with in_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    tiles = []
    gather_tiles(data, ctx=["root"], acc=tiles)

    title = (data.get("dashboardMetadata", {}) or {}).get("name") or in_path.stem
    var_map = parse_variables(data)

    md = render_markdown(tiles, title, var_map)

    out_path.write_text(md, encoding="utf-8")
    print(f"Wrote Markdown with {len(tiles)} tiles -> {out_path}")

if __name__ == "__main__":
    main()
```
