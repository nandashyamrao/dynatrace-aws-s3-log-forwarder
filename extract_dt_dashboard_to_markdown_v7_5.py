#!/usr/bin/env python3
"""
Dynatrace Dashboard -> Markdown extractor (v7.5)

- Reads ALL *.json files in the current folder.
- For each JSON, writes <stem>_TileQueries.md
- Markdown title: "<FileName> - Dynatrace Dashboard Tile Queries Details"
- Minimal DQL formatting only:
  * Split on '|' so each stage is on its own line
  * Soft-wrap very long lines at top-level commas with a simple indent
- Includes **Variables** section:
  * Extracts variable DQL (supports 'input', 'query', 'dql', 'definition', 'data', 'string', 'value', 'expression')
  * Shows where each variable is used: tile name + query number
"""

import json
import re
import sys
from pathlib import Path
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

# -------------- helpers --------------
def try_json_decode(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    s = value.strip()
    if not (s.startswith("{") or s.startswith("[") or s.startswith('"')):
        return value
    for _ in range(3):
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
            if isinstance(k, str) and k.lower() in QUERY_KEYS | {"value","expression"}:
                out.extend(normalize_query_value(v))
            if isinstance(v, dict) and "string" in v and isinstance(v["string"], str):
                out.extend(normalize_query_value(v["string"]))
        for k in ("query", "dql", "ql"):
            if k in val:
                out.extend(normalize_query_value(val[k]))
    return [s for s in (q.strip() for q in out) if s]

def unique_keep_order(items: List[str]) -> List[str]:
    seen=set(); out=[]
    for x in items:
        if x not in seen:
            seen.add(x); out.append(x)
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
    if not candidates and isinstance(node.get("visualConfig"), dict):
        for k, vv in node["visualConfig"].items():
            if isinstance(vv, str) and vv.strip() and k.lower() in ("visualization","type","charttype","graphtype"):
                candidates.append(vv.strip())
    return candidates[0] if candidates else "—"

def gather_tiles(node: Json, ctx: List[str], acc: List[Dict[str, Any]]):
    if isinstance(node, dict):
        display = next((node[k].strip() for k in NAME_KEYS if isinstance(node.get(k), str) and node[k].strip()), None)
        tile_type = next((node[k].strip() for k in TYPE_KEYS if isinstance(node.get(k), str) and node[k].strip()), None)
        descs = [node[k].strip() for k in DESC_KEYS if isinstance(node.get(k), str) and node[k].strip()]
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
                "queries": unique_keep_order(queries),
            })
        for k, v in node.items():
            gather_tiles(v, ctx + [k], acc)
    elif isinstance(node, list):
        for i, it in enumerate(node):
            gather_tiles(it, ctx + [f"[{i}]"], acc)

def first_line(s: str, maxlen=96) -> str:
    fl = s.splitlines()[0].strip()
    return (fl[:maxlen] + "…") if len(fl) > maxlen else fl

# -------------- variables --------------
DQL_HINTS = ("fetch ","filter ","| filter","summarize","timeseries","lookup","join","parse","fields")
VAR_VALUE_KEYS = ("input","query","dql","definition","data","string","value","expression")

def looks_like_dql(text: str) -> bool:
    return any(h in text.strip().lower() for h in DQL_HINTS)

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
        if not name: return
        name = name.strip().strip("${} ")
        if not name: return
        if dql:
            var_map[name] = dql.strip()
        elif name not in var_map:
            var_map[name] = ""

    for path in (["variables"], ["dashboardMetadata","variables"], ["inputs"]):
        node = get_nested(data, path)
        if isinstance(node, list):
            for v in node:
                if isinstance(v, dict):
                    name = v.get("name") or v.get("key") or v.get("id")
                    add_var(name, extract_dql_from_obj(v))

    if not var_map:
        def walk(n: Json):
            if isinstance(n, dict):
                name = n.get("name") or n.get("key") or n.get("id")
                if isinstance(name, str) and name.strip():
                    dql = extract_dql_from_obj(n)
                    if dql:
                        add_var(name, dql)
                for vv in n.values():
                    walk(vv)
            elif isinstance(n, list):
                for it in n:
                    walk(it)
        walk(data)
    return var_map

def build_var_usage(tiles: List[Dict[str, Any]], var_map: Dict[str, str]):
    """Return usage dict: var -> list of (tile_name, query_index). Also annotate tiles with vars_used."""
    usage = {vn: [] for vn in var_map.keys()}
    for t in tiles:
        used_here = set()
        for idx, q in enumerate(t["queries"], 1):
            for vn in var_map.keys():
                if re.search(rf"(\$\{{{re.escape(vn)}\}}|\${re.escape(vn)}\b)", q):
                    usage[vn].append((t["name"], idx))
                    used_here.add(vn)
        t["vars_used"] = sorted(used_here)
    return usage

# -------------- minimal DQL formatting --------------
MAX_LINE = 120

def _split_on_pipes(text: str) -> str:
    out, i, in_s, qch, buf = [], 0, False, '', ''
    while i < len(text):
        ch = text[i]
        if in_s:
            buf += ch
            if ch == qch:
                in_s = False
            elif ch == '\\' and i+1 < len(text):
                buf += text[i+1]; i += 1
        else:
            if ch in ('"', "'"):
                in_s = True; qch = ch; buf += ch
            elif ch == '|':
                out.append(buf.strip()); buf = '| '
            else:
                buf += ch
        i += 1
    out.append(buf.strip())
    return '\n'.join(part if part.startswith('| ') else part for part in out if part.strip())

def _soft_wrap_top_level_commas(line: str, max_len=MAX_LINE, indent='    '):
    if len(line) <= max_len:
        return line
    args, buf, lvl, in_s, qch = [], '', 0, False, ''
    for i,ch in enumerate(line):
        if in_s:
            buf += ch
            if ch == qch:
                in_s = False
            elif ch == '\\' and i+1 < len(line):
                buf += line[i+1]
            continue
        if ch in ('"', "'"):
            in_s = True; qch = ch; buf += ch; continue
        if ch in '([{': lvl += 1
        elif ch in ')]}': lvl = max(0, lvl-1)
        if ch == ',' and lvl == 0:
            args.append(buf.strip()); buf = ''
        else:
            buf += ch
    if buf.strip(): args.append(buf.strip())
    if len(args) <= 1:
        return line
    return (',\n' + indent).join(args)

def format_dql_light(q: str) -> str:
    q = q.replace('\r\n', '\n').strip()
    s = _split_on_pipes(q)
    lines = []
    for ln in s.splitlines():
        if ln.startswith('| '):
            base = '| ' + _soft_wrap_top_level_commas(ln[2:].strip(), MAX_LINE, indent='    ')
            lines.append(base)
        else:
            lines.append(_soft_wrap_top_level_commas(ln.strip(), MAX_LINE, indent='    '))
    return '\n'.join(lines).strip()

# -------------- markdown --------------
def anchor_for(name: str) -> str:
    return re.sub(r'[^a-z0-9\- ]+', '', name.lower()).replace(' ', '-')

def render_markdown(tiles: List[Dict[str, Any]], file_name: str, var_map: Dict[str, str]) -> str:
    title = f"{file_name} - Dynatrace Dashboard Tile Queries Details"
    ts = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M")
    total_q = sum(len(t["queries"]) for t in tiles)
    tiles_sorted = sorted(tiles, key=lambda t: (t["name"] == "Dashboard Spacer Cell", t["name"].lower()))

    usage = build_var_usage(tiles_sorted, var_map)

    md = []
    md.append(f"# {title}\n\n")
    md.append(f"_Generated on {ts}. Tiles with queries: **{len(tiles_sorted)}**. Total queries: **{total_q}**._\n\n")
    if var_map:
        md.append(f"**Detected dashboard variables:** {' '.join(f'`{v}`' for v in var_map.keys())}\n\n")
    md.append("---\n\n")

    if var_map:
        md.append("## Variables\n")
        for vn, vdql in var_map.items():
            md.append(f"### `{vn}`\n\n")
            # usage list with tile + query number
            places = usage.get(vn, [])
            if places:
                md.append("Used in:\n")
                for (tname, qidx) in places:
                    md.append(f"- [{tname}](#{anchor_for(tname)}) — Query {qidx}\n")
                md.append("\n")
            if vdql:
                md.append("```dql\n")
                md.append(format_dql_light(vdql))
                md.append("\n```\n\n")
            else:
                md.append("_Definition not found in export._\n\n")
        md.append("---\n\n")

    # Overview
    md.append("## Overview\n")
    md.append("| # | Tile | Type | Visualization | Vars Used | Queries | Preview |\n|---:|---|---|---|---|---:|---|\n")
    for i, t in enumerate(tiles_sorted, 1):
        link = f"[{t['name']}](#{anchor_for(t['name'])})"
        preview = first_line(t["queries"][0]) if t["queries"] else ""
        vars_list = " ".join(f'`{v}`' for v in t.get("vars_used", [])) or "—"
        md.append(f"| {i} | {link} | {t['type']} | {t['visualization']} | {vars_list} | {len(t['queries'])} | `{preview}` |\n")
    md.append("\n---\n\n")

    # Details per tile
    for t in tiles_sorted:
        md.append(f"## {t['name']}\n\n")
        md.append(f"**Type:** `{t['type']}`  \n")
        md.append(f"**Visualization:** `{t['visualization']}`  \n")
        md.append(f"**Context:** `{t['context']}`\n\n")
        if t["description"]:
            md.append("> " + t["description"].replace("\n", "\n> ") + "\n\n")
        for qi, q in enumerate(t["queries"], 1):
            pretty = format_dql_light(q)
            md.append(f"<details>\n<summary><strong>Query {qi}</strong> — {len(pretty.splitlines())} lines</summary>\n\n")
            md.append("```dql\n")
            md.append(pretty)
            md.append("\n```\n")
            md.append("\n</details>\n\n")
        md.append("---\n\n")
    return "".join(md)

# -------------- main --------------
def main():
    json_files = sorted(Path('.').glob('*.json'))
    if not json_files:
        print("No *.json files found in the current folder.", file=sys.stderr)
        sys.exit(1)

    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"Skipping {jf.name}: failed to parse JSON ({e})", file=sys.stderr)
            continue

        # collect tiles
        tiles: List[Dict[str, Any]] = []
        gather_tiles(data, ctx=['root'], acc=tiles)

        # variables
        var_map = parse_variables(data)

        md = render_markdown(tiles, file_name=jf.name, var_map=var_map)
        out_path = jf.with_name(f"{jf.stem}_TileQueries.md")
        out_path.write_text(md, encoding='utf-8')
        print(f"✓ Wrote {out_path}")

if __name__ == '__main__':
    main()
