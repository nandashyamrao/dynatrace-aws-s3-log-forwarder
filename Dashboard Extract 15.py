#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynatrace Dashboard -> Markdown extractor (v15)

Fixes & features vs the attached version:
- Variables section renders a compact **4-column table** of tile links (no "Query #" column).
- DQL formatter:
  * Splits stages on `|` while preserving original indentation.
  * Does **not** split/comment-wrap lines starting with `//` or the comment portion after `//`.
  * Soft-wraps very long concat(...) calls only, leaving logic/flow intact.
- Scans all *.json in the current folder; writes <stem>_TileQueries.md.
- Markdown title: "<JsonFileName> - Tile Query Details".
"""

import json, re, sys, datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

QUERY_KEYS = {"query","dql","ql","metricSelector","metricExpression","metricExpressions","metric"}
DESC_KEYS  = {"description","tileDescription","markdown","notes"}
NAME_KEYS  = {"name","title","customName","displayName"}
TYPE_KEYS  = {"tileType","type"}

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
            kl = k.lower() if isinstance(k, str) else k
            if isinstance(kl, str) and (kl in QUERY_KEYS or kl in {"value","expression"}):
                out.extend(normalize_query_value(v))
            if isinstance(v, dict) and "string" in v and kl in QUERY_KEYS:
                out.extend(normalize_query_value(v["string"]))
        for k in ("query","dql","ql"):
            if k in val:
                out.extend(normalize_query_value(val[k]))
    return [s for s in (q.strip() for q in out) if s]

def unique(items: List[str]) -> List[str]:
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
    v = get_nested(node, ["visualConfig","type"])
    if isinstance(v, str) and v.strip():
        candidates.append(v.strip())
    for k in ("visualization","viz","chartType","graphType"):
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
                "queries": unique(queries),
            })
        for k, v in node.items():
            gather_tiles(v, ctx + [k], acc)
    elif isinstance(node, list):
        for i, it in enumerate(node):
            gather_tiles(it, ctx + [f"[{i}]"], acc)

def first_line(s: str, maxlen: int = 96) -> str:
    fl = s.splitlines()[0].strip()
    return (fl[:maxlen] + "…") if len(fl) > maxlen else fl

# -------- Variables parsing --------
DQL_HINTS = ("fetch ","filter ","| filter","summarize","timeseries","lookup","join","parse","fields","by ")
VAR_VALUE_KEYS = ("input","query","dql","definition","data","string","value","expression")

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
        if not name: return
        name = name.strip().strip("${} ")
        if not name: return
        if dql:
            var_map[name] = dql.strip()
        elif name not in var_map:
            var_map[name] = ""

    containers = []
    for path in (["variables"], ["dashboardMetadata","variables"], ["inputs"]):
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

def build_var_usage(tiles: List[Dict[str, Any]], var_map: Dict[str, str]):
    usage: Dict[str, List[str]] = {vn: [] for vn in var_map.keys()}
    for t in tiles:
        used_here = set()
        qs = t.get("queries", [])
        for q in qs:
            for vn in var_map.keys():
                if re.search(rf"(\$\{{{re.escape(vn)}\}}|\${re.escape(vn)}\b)", q):
                    used_here.add(vn)
        for vn in used_here:
            usage[vn].append(t["name"])
        t["vars_used"] = sorted(used_here)
    return usage

# -------- Minimal DQL formatting --------
MAX_LINE = 140

def _split_pipes_preserve_indent(text: str) -> str:
    """Split on | outside strings; preserve indentation; don't split in comments."""
    lines = text.replace('\r\n', '\n').split('\n')
    result_lines = []
    for line in lines:
        if not line.strip():
            result_lines.append(line); continue
        # If the line begins with comment markers, leave it untouched
        leading_ws = len(line) - len(line.lstrip(' '))
        stripped = line.lstrip()
        if stripped.startswith('//') or stripped.startswith('#'):
            result_lines.append(line); continue

        # If there is an inline // comment, protect the comment tail from splitting
        comment_pos = line.find('//')
        code_part = line if comment_pos == -1 else line[:comment_pos]
        comment_tail = '' if comment_pos == -1 else line[comment_pos:]

        # Split only the code_part by pipes, while tracking strings
        buf=''; out_parts=[]; in_s=False; qch=''; i=0
        while i < len(code_part):
            ch = code_part[i]
            if in_s:
                buf += ch
                if ch == qch:
                    in_s = False
                elif ch == '\\' and i+1 < len(code_part):
                    buf += code_part[i+1]; i += 1
            else:
                if ch in ('"', "'"):
                    in_s = True; qch = ch; buf += ch
                elif ch == '|':
                    out_parts.append(buf.rstrip()); buf = '|'
                else:
                    buf += ch
            i += 1
        out_parts.append(buf.rstrip())

        indent = ' ' * leading_ws
        if len(out_parts) == 1:
            new_line = line
        else:
            new_lines = []
            first = out_parts[0]
            if first.strip():
                new_lines.append(indent + first.strip())
            for part in out_parts[1:]:
                if part.strip():
                    part_str = part if part.startswith('|') else '|' + part
                    if part_str.startswith('|') and not part_str.startswith('| '):
                        part_str = '| ' + part_str[1:]
                    new_lines.append(indent + part_str.strip())
            new_line = '\n'.join(new_lines)

        # Reattach the comment tail (unchanged) to the last physical line
        if comment_tail:
            parts = new_line.split('\n')
            parts[-1] = parts[-1] + ' ' + comment_tail
            new_line = '\n'.join(parts)

        result_lines.append(new_line)
    return '\n'.join(result_lines)

def _soft_wrap_concat_calls(text: str, max_len=MAX_LINE, inner_indent='      '):
    s = text
    pattern = re.compile(r'(?i)concat\s*\(', re.M)
    i = 0
    while True:
        m = pattern.search(s, i)
        if not m: break
        start = m.end() - 1
        lvl=1; in_s=False; qch=''; j=start
        while j < len(s) - 1:
            j += 1; ch = s[j]
            if in_s:
                if ch == qch: in_s=False
                elif ch == '\\' and j+1 < len(s): j += 1
                continue
            if ch in ('"', "'"): in_s=True; qch=ch; continue
            if ch == '(': lvl += 1
            elif ch == ')':
                lvl -= 1
                if lvl == 0: break
        if lvl != 0: i = m.end(); continue
        call = s[m.start():j+1]
        if len(call) <= max_len: i = j + 1; continue
        args_str = s[start+1:j]
        args, buf, lvl2, in_s2, q2 = [], '', 0, False, ''
        for k,ch in enumerate(args_str):
            if in_s2:
                buf += ch
                if ch == q2: in_s2=False
                elif ch == '\\' and k+1 < len(args_str): buf += args_str[k+1]
                continue
            if ch in ('"', "'"): in_s2=True; q2=ch; buf += ch; continue
            if ch in '([{': lvl2 += 1
            elif ch in ')]}': lvl2 = max(0, lvl2-1)
            if ch == ',' and lvl2 == 0:
                args.append(buf.strip()); buf = ''
            else:
                buf += ch
        if buf.strip(): args.append(buf.strip())
        inner = (',\n' + inner_indent).join(a for a in args if a)
        formatted = f"concat(\n{inner_indent}{inner}\n  )"
        s = s[:m.start()] + formatted + s[j+1:]
        i = m.start() + len(formatted)
    return s

def format_dql_safe(q: str) -> str:
    s = _split_pipes_preserve_indent(q)
    s = _soft_wrap_concat_calls(s, max_len=MAX_LINE)
    return s.strip()

# -------- Markdown rendering --------
def anchor_for(name: str) -> str:
    return re.sub(r'[^a-z0-9\- ]+', '', name.lower()).replace(' ', '-')

def chunk(lst: List[str], n: int) -> List[List[str]]:
    return [lst[i:i+n] for i in range(0, len(lst), n)]

def render_markdown(tiles: List[Dict[str, Any]], json_filename: str, var_map: Dict[str, str]) -> str:
    title = f"{json_filename} - Tile Query Details"
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
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
            # Build compact 4-column table (tile links only)
            tiles_using = sorted(set(tname for tname in usage.get(vn, [])), key=str.lower)
            if tiles_using:
                md.append("| Tile | Tile | Tile | Tile |\n|---|---|---|---|\n")
                rows = chunk(tiles_using, 4)
                for row in rows:
                    cols = [f"[{t}](#{anchor_for(t)})" for t in row]
                    while len(cols) < 4:
                        cols.append("")
                    md.append("| " + " | ".join(cols) + " |\n")
                md.append("\n")
            if vdql:
                md.append("```sql\n")
                md.append(format_dql_safe(vdql))
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
        if t.get("description"):
            md.append("> " + t["description"].replace("\n", "\n> ") + "\n\n")
        for qi, q in enumerate(t["queries"], 1):
            pretty = format_dql_safe(q)
            lines = len(pretty.splitlines())
            md.append(f"<details>\n<summary><strong>Query {qi}</strong> — {lines} line{'s' if lines!=1 else ''}</summary>\n\n")
            md.append("```sql\n")
            md.append(pretty)
            md.append("\n```\n")
            md.append("\n</details>\n\n")
        md.append("---\n\n")
    return "".join(md)

# -------- main --------
def main():
    json_files = sorted(Path('.').glob('*.json'))
    if not json_files:
        print("No *.json files found in the current folder.")
        sys.exit(0)

    for in_path in json_files:
        try:
            data = json.loads(in_path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"Skipping {in_path.name}: failed to parse JSON ({e})", file=sys.stderr)
            continue

        tiles: List[Dict[str, Any]] = []
        gather_tiles(data, ctx=['root'], acc=tiles)

        var_map = parse_variables(data)

        md = render_markdown(tiles, json_filename=in_path.name, var_map=var_map)
        out_path = in_path.with_name(f"{in_path.stem}_TileQueries.md")
        out_path.write_text(md, encoding='utf-8')
        print(f"✓ Wrote {out_path}")

if __name__ == '__main__':
    main()
