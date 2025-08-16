#!/usr/bin/env python3
"""
Dynatrace Dashboard -> Markdown extractor (v7.7)

Enhancements:
- Processes all JSON files in the current folder
- Names output files <stem>_TileQueries.md
- Markdown title: <FileName> - Dynatrace Dashboard Tile Queries Details
- Keeps v7.1 variables section logic (supports 'input' key) + usage tracking
- Pretty DQL printer for readability
"""

import sys, json, pathlib, datetime, re
from typing import Any, Dict, List, Union

Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

QUERY_KEYS = {"query", "dql", "ql", "metricSelector", "metricExpression", "metricExpressions", "metric"}
DESC_KEYS = {"description", "tileDescription", "markdown", "notes"}
NAME_KEYS = {"name", "title", "customName", "displayName"}
TYPE_KEYS = {"tileType", "type"}

# ----------------- helpers -----------------
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
                "visualization": detect_visualization(node),
                "description": " | ".join(descs) if descs else "",
                "queries": unique(queries),
            })

        for k, v in node.items():
            gather_tiles(v, ctx + [k], acc)

    elif isinstance(node, list):
        for idx, item in enumerate(node):
            gather_tiles(item, ctx + [f"[{idx}]"], acc)

def first_line(s: str, maxlen: int = 96) -> str:
    fl = s.splitlines()[0].strip()
    return (fl[:maxlen] + "…") if len(fl) > maxlen else fl

# -------- Variables parsing (supports 'input') --------
DQL_HINTS = ("fetch ", "filter ", "| filter", "summarize", "timeseries", "lookup", "join", "parse")
VAR_VALUE_KEYS = ("input", "query", "dql", "definition", "data", "string", "value", "expression")

def looks_like_dql(text: str) -> bool:
    t = text.strip().lower()
    return any(h in t for h in DQL_HINTS)

def extract_dql_from_obj(obj: Dict[str, Any]) -> str:
    for key in VAR_VALUE_KEYS:
        val = obj.get(key)
        if isinstance(val, str) and looks_like_dql(val):
            return val.strip()
        if isinstance(val, dict):
            for kk in VAR_VALUE_KEYS:
                vv = val.get(kk)
                if isinstance(vv, str) and looks_like_dql(vv):
                    return vv.strip()
    for v in obj.values():
        if isinstance(v, str) and looks_like_dql(v):
            return v.strip()
        if isinstance(v, dict):
            for vv in v.values():
                if isinstance(vv, str) and looks_like_dql(vv):
                    return vv.strip()
    return ""

def parse_variables(data: Dict[str, Any]) -> Dict[str, str]:
    var_map: Dict[str, str] = {}

    def add_var(name: str, dql: str):
        if not name:
            return
        name = name.strip().strip("${} ")
        if not name:
            return
        if dql:
            var_map[name] = dql.strip()
        elif name not in var_map:
            var_map[name] = ""

    containers = []
    for path in (["variables"], ["dashboardMetadata", "variables"], ["inputs"]):
        node = get_nested(data, path)
        if isinstance(node, list):
            containers.append(node)

    for arr in containers:
        for v in arr:
            if not isinstance(v, dict):
                continue
            name = v.get("name") or v.get("key") or v.get("id")
            dql = extract_dql_from_obj(v)
            add_var(name, dql)

    if not var_map:
        def walk(n: Json):
            if isinstance(n, dict):
                name = n.get("name") or n.get("key") or n.get("id")
                if isinstance(name, str) and name.strip():
                    dql = extract_dql_from_obj(n)
                    if dql:
                        add_var(name, dql)
                for v in n.values():
                    walk(v)
            elif isinstance(n, list):
                for it in n:
                    walk(it)
        walk(data)

    return var_map

def build_var_usage(tiles: List[Dict[str, Any]], var_map: Dict[str, str]) -> Dict[str, List[str]]:
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

# ----------------- Minimal DQL formatting -----------------
def format_dql_query(q: str) -> str:
    q = q.replace("\r\n", "\n").strip()
    # just break on pipe for readability
    parts = []
    buf, in_s, qch = "", False, ""
    for ch in q:
        if in_s:
            buf += ch
            if ch == qch:
                in_s = False
        else:
            if ch in ("'", '"'):
                in_s, qch = True, ch
                buf += ch
            elif ch == "|":
                parts.append(buf.strip())
                buf = "| "
            else:
                buf += ch
    parts.append(buf.strip())
    return "\n".join(p for p in parts if p)

# ----------------- Markdown rendering -----------------
def render_markdown(tiles, title: str, var_map: Dict[str, str]) -> str:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    total_q = sum(len(t["queries"]) for t in tiles)
    tiles_sorted = sorted(tiles, key=lambda t: (t["name"] == "Dashboard Spacer Cell", t["name"].lower()))
    usage = build_var_usage(tiles_sorted, var_map)

    md = []
    md.append(f"# {title} - Dynatrace Dashboard Tile Queries Details\n\n")
    md.append(f"_Generated on {ts}. Tiles with queries: **{len(tiles_sorted)}**. Total queries: **{total_q}**._\n\n")
    if var_map:
        md.append(f"**Detected dashboard variables:** {' '.join(f'`{v}`' for v in var_map.keys())}\n\n")
    md.append("---\n\n")

    if var_map:
        md.append("## Variables\n")
        for vn, vdql in var_map.items():
            md.append(f"### `{vn}`\n\n")
            tiles_for_var = usage.get(vn, [])
            if tiles_for_var:
                links = ", ".join(f"[{t}](#{anchor_for(t)})" for t in tiles_for_var)
                md.append(f"Used in: {links}\n\n")
            if vdql:
                md.append("```sql\n")
                md.append(format_dql_query(vdql))
                md.append("\n```\n\n")
            else:
                md.append("_Definition not found in export._\n\n")
        md.append("---\n\n")

    md.append("## Overview\n")
    md.append("| # | Tile | Type | Visualization | Vars Used | Queries | Preview |\n|---:|---|---|---|---|---:|---|\n")
    for i, t in enumerate(tiles_sorted, 1):
        link = f"[{t['name']}](#{anchor_for(t['name'])})"
        preview = first_line(t["queries"][0]) if t["queries"] else ""
        vars_list = " ".join(f"`{v}`" for v in t.get("vars_used", [])) or "—"
        md.append(f"| {i} | {link} | {t['type']} | {t['visualization']} | {vars_list} | {len(t['queries'])} | `{preview}` |\n")
    md.append("\n---\n\n")

    for i, t in enumerate(tiles_sorted, 1):
        md.append(f"## {t['name']}\n\n")
        md.append(f"**Type:** `{t['type']}`  \n")
        md.append(f"**Visualization:** `{t['visualization']}`  \n")
        md.append(f"**Context:** `{t['context']}`\n\n")
        if t.get("vars_used"):
            md.append("**Vars Used:** " + ", ".join(f"`{v}`" for v in t["vars_used"]) + "\n\n")
        if t["description"]:
            md.append("> " + t["description"].replace("\n", "\n> ") + "\n\n")
        for qi, q in enumerate(t["queries"], 1):
            pretty = format_dql_query(q)
            lines = len(pretty.splitlines())
            md.append(f"<details>\n<summary><strong>Query {qi}</strong> — {lines} line{'s' if lines!=1 else ''}</summary>\n\n")
            md.append("```sql\n")
            md.append(pretty)
            md.append("\n```\n")
            md.append("</details>\n\n")
        md.append("---\n\n")
    return "".join(md)

# -------- main --------
def main():
    cwd = pathlib.Path(".")
    json_files = list(cwd.glob("*.json"))
    if not json_files:
        print("No JSON files found in current folder.")
        sys.exit(0)

    for in_path in json_files:
        with in_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        tiles: List[Dict[str, Any]] = []
        gather_tiles(data, ctx=["root"], acc=tiles)

        title = (data.get("dashboardMetadata", {}) or {}).get("name") or in_path.stem
        var_map = parse_variables(data)
        _ = build_var_usage(tiles, var_map)

        md = render_markdown(tiles, title, var_map)
        out_path = in_path.with_name(in_path.stem + "_TileQueries.md")
        out_path.write_text(md, encoding="utf-8")
        print(f"Wrote Markdown with {len(tiles)} tiles -> {out_path}")

if __name__ == "__main__":
    main()
