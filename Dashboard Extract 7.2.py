#!/usr/bin/env python3
"""
Dynatrace Dashboard -> Markdown extractor (v7.1)

What this does
- Strong DQL pretty-printer for readable grouping/indentation like:
    fetch spans
    | filter in(
        dt.entity.service,
        classicEntitySelector(
          concat(
            "type(SERVICE)",
            ...
          )
        )
      )
    | filter ...
    | summarize
        totalErrors = count(),
        ...
      by service.name, k8s.namespace.name
    | sort totalErrors desc

- Variables section with each variable's DQL (supports 'input' key) + links to tiles using it
- Overview table includes "Vars Used" + Visualization column
- Collapsible query details per tile
- Writes Markdown with ```sql fences

Usage:
    python3 extract_dt_dashboard_to_markdown_v7_1.py dashboard.json [output.md]
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
                # match $var or ${var}
                if re.search(rf"(\$\{{{re.escape(vn)}\}}|\${re.escape(vn)}\b)", q):
                    used.add(vn)
        for vn in used:
            usage[vn].append(t["name"])
        t["vars_used"] = sorted(list(used))
    return usage

def anchor_for(name: str) -> str:
    return re.sub(r'[^a-z0-9\- ]+', '', name.lower()).replace(' ', '-')

# ----------------- DQL pretty printer -----------------

MAX_LINE = 88

def _split_pipes(text: str) -> str:
    """Split on | outside strings; start each pipe stage on its own line."""
    out, i, in_s, qch = [], 0, False, ''
    buf = ''
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
                out.append(buf.strip())
                buf = '| '
            else:
                buf += ch
        i += 1
    out.append(buf.strip())
    return '\n'.join(part if part.startswith('| ') else part for part in out if part.strip())

def _format_function_args(s: str, func_names=('concat',), max_line=MAX_LINE):
    """
    Force multiline for selected functions (e.g., concat). Also wrap any function
    whose call length exceeds max_line.
    """
    def wrap_args(fn, args_str, inner_indent='      '):  # 6 spaces inside concat
        # split args by comma respecting strings and parens
        args, buf, lvl, in_s, qch = [], '', 0, False, ''
        for i,ch in enumerate(args_str):
            if in_s:
                buf += ch
                if ch == qch:
                    in_s = False
                elif ch == '\\' and i+1 < len(args_str):
                    buf += args_str[i+1]
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
        inner = (',\n' + inner_indent).join(a for a in args if a)
        return f"{fn}(\n{inner_indent}{inner}\n  )"  # closing aligns 2 spaces from left (top-level indent)

    # 1) force for target functions
    pattern = re.compile(r'(?i)\b(' + '|'.join(re.escape(n) for n in func_names) + r')\s*\(', re.M)
    i = 0
    while True:
        m = pattern.search(s, i)
        if not m:
            break
        fn = m.group(1)
        start = m.end()-1
        lvl, in_s, qch = 1, False, ''
        j = start
        while j < len(s)-1:
            j += 1
            ch = s[j]
            if in_s:
                if ch == qch:
                    in_s = False
                elif ch == '\\' and j+1 < len(s):
                    j += 1
                continue
            if ch in ('"', "'"):
                in_s = True; qch = ch; continue
            if ch == '(':
                lvl += 1
            elif ch == ')':
                lvl -= 1
                if lvl == 0:
                    break
        args_str = s[start+1:j]
        formatted = wrap_args(fn, args_str)
        s = s[:m.start()] + formatted + s[j+1:]
        i = m.start() + len(formatted)

    # 2) wrap any overlong function call lines
    def wrap_overlong(match):
        fn = match.group(1)
        args_str = match.group(2)
        call = f"{fn}({args_str})"
        if len(call) <= max_line:
            return call
        return wrap_args(fn, args_str, inner_indent='      ')
    s = re.sub(r'(\b[a-zA-Z_][a-zA-Z0-9_]*)\(([^()\n]*?(?:\([^)]*\)[^()]*)*?)\)', wrap_overlong, s)
    return s

def _break_by_and_sort(text: str) -> str:
    text = re.sub(r'(?i)\s+\bby\b\s+', '\nby ', text)
    text = re.sub(r'(?i)\s+\bsort\b\s+', '\nsort ', text)
    return text

def _summarize_multiline(text: str) -> str:
    # Make summarize block multi-line
    def repl(m):
        tail = m.group(1)
        # split on commas respecting nesting
        args, buf, lvl, in_s, qch = [], '', 0, False, ''
        i = 0
        while i < len(tail):
            ch = tail[i]
            if in_s:
                buf += ch
                if ch == qch:
                    in_s = False
                elif ch == '\\' and i+1 < len(tail):
                    buf += tail[i+1]; i += 1
                i += 1; continue
            if ch in ('"', "'"):
                in_s = True; qch = ch; buf += ch; i += 1; continue
            if ch in '([{': lvl += 1
            elif ch in ')]}': lvl = max(0, lvl-1)
            if ch == ',' and lvl == 0:
                args.append(buf.strip()); buf = ''
            elif tail.startswith('\nby ', i):
                break
            else:
                buf += ch
            i += 1
        if buf.strip(): args.append(buf.strip())
        return 'summarize\n  ' + '\n  '.join(', '.join(args).split(', '))
    return re.sub(r'(?i)summarize\s+([^|\n]+)', repl, text)

def format_dql_query(q: str) -> str:
    """
    Pretty-print DQL with:
      - Two-space top-level indent
      - Six-space indent for concat(...) arguments
      - Pipes on their own lines
      - Wrapped long function calls and multiline summarize blocks
    """
    q = q.replace("\r\n", "\n").strip()
    s = _split_pipes(q)
    s = _break_by_and_sort(s)
    s = _format_function_args(s, func_names=('concat','classicEntitySelector','in','if'))
    s = _summarize_multiline(s)

    # Final indentation pass for parentheses blocks
    lines = [ln.rstrip() for ln in s.splitlines()]
    indented, level = [], 0
    for ln in lines:
        stripped = ln.lstrip()
        # Reduce before writing if closing bracket first
        if stripped.startswith((')',']','}')):
            level = max(0, level-1)
        # Top-level: prefix two spaces unless it's the very first line
        prefix = '  ' if not stripped.startswith('| ') and not stripped.startswith('##') else ''
        indented.append(prefix + ('  '*level) + stripped)
        # Adjust for next line
        opens = stripped.count('(')+stripped.count('{')+stripped.count('[')
        closes = stripped.count(')')+stripped.count('}')+stripped.count(']')
        level = max(0, level + opens - closes)
    s = '\n'.join(indented)
    # Clean up multiple blank lines
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

# ------------------------------------------------------

def render_markdown(tiles, title: str, var_map: Dict[str, str]) -> str:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    total_q = sum(len(t["queries"]) for t in tiles)
    tiles_sorted = sorted(tiles, key=lambda t: (t["name"] == "Dashboard Spacer Cell", t["name"].lower()))
    usage = build_var_usage(tiles_sorted, var_map)

    md = []
    md.append(f"# {title} — Extracted Queries\n\n")
    md.append(f"_Generated on {ts}. Tiles with queries: **{len(tiles_sorted)}**. Total queries: **{total_q}**._\n\n")
    if var_map:
        md.append(f"**Detected dashboard variables:** {' '.join(f'`{v}`' for v in var_map.keys())}\n\n")
    md.append("---\n\n")

    # Variables section (list each variable once with DQL + usage links)
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

    # Overview table (TOC + summary)
    md.append("## Overview\n")
    md.append("| # | Tile | Type | Visualization | Vars Used | Queries | Preview |\n|---:|---|---|---|---|---:|---|\n")
    for i, t in enumerate(tiles_sorted, 1):
        link = f"[{t['name']}](#{anchor_for(t['name'])})"
        preview = first_line(t["queries"][0]) if t["queries"] else ""
        vars_list = " ".join(f"`{v}`" for v in t.get("vars_used", [])) or "—"
        md.append(f"| {i} | {link} | {t['type']} | {t['visualization']} | {vars_list} | {len(t['queries'])} | `{preview}` |\n")
    md.append("\n---\n\n")

    # Details per tile
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
            md.append("\n</details>\n\n")
        md.append("---\n\n")
    return "".join(md)

# -------- main --------

def main():
    if len(sys.argv) < 2:
        print("Usage: extract_dt_dashboard_to_markdown_v7_1.py <dashboard.json> [output.md]", file=sys.stderr)
        sys.exit(1)

    in_path = pathlib.Path(sys.argv[1])
    out_path = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(in_path.stem + "_queries.md")

    with in_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    tiles: List[Dict[str, Any]] = []
    gather_tiles(data, ctx=["root"], acc=tiles)

    title = (data.get("dashboardMetadata", {}) or {}).get("name") or in_path.stem
    var_map = parse_variables(data)
    # compute usage map before rendering so the Vars Used column is accurate
    _ = build_var_usage(tiles, var_map)

    md = render_markdown(tiles, title, var_map)

    out_path.write_text(md, encoding="utf-8")
    print(f"Wrote Markdown with {len(tiles)} tiles -> {out_path}")

if __name__ == "__main__":
    main()
