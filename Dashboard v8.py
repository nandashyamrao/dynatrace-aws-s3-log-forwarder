#!/usr/bin/env python3
"""
Dynatrace Dashboard -> Markdown extractor (v7.3)

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

- Also formats block-style queries (no pipes) with:
    timeseries ...
    by:
      ...
    filter:
      ...
    fields
      ...

- Variables section with each variable's DQL (supports 'input') + links to tiles using it
- Overview table includes "Vars Used" + Visualization column
- Collapsible query details per tile
- Writes Markdown with ```dql fences

Usage:
    python3 extract_dt_dashboard_to_markdown_v7_3.py dashboard.json [output.md]
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

# ----------------- generic helpers -----------------

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

def normalize_query_value(val: Any):
    out = []
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
        for k in ("query","dql","ql"):
            if k in val:
                out.extend(normalize_query_value(val[k]))
    return [s for s in (q.strip() for q in out) if s]

def unique(items):
    seen = set(); out=[]
    for x in items:
        if x not in seen:
            seen.add(x); out.append(x)
    return out

def get_nested(d: Dict[str, Any], path):
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

def gather_tiles(node: Json, ctx: list, acc: list):
    if isinstance(node, dict):
        display = next((node[k].strip() for k in NAME_KEYS if isinstance(node.get(k), str) and node[k].strip()), None)
        tile_type = next((node[k].strip() for k in TYPE_KEYS if isinstance(node.get(k), str) and node[k].strip()), None)
        descs = [node[k].strip() for k in DESC_KEYS if isinstance(node.get(k), str) and node[k].strip()]
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
            gather_tiles(v, ctx+[k], acc)
    elif isinstance(node, list):
        for i, it in enumerate(node):
            gather_tiles(it, ctx+[f"[{i}]"], acc)

def first_line(s: str, maxlen=96) -> str:
    fl = s.splitlines()[0].strip()
    return (fl[:maxlen] + "…") if len(fl) > maxlen else fl

# ----------------- variables -----------------

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
        if dql: var_map[name] = dql.strip()
        elif name not in var_map: var_map[name] = ""

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
                    d = extract_dql_from_obj(n)
                    if d: add_var(name, d)
                for vv in n.values(): walk(vv)
            elif isinstance(n, list):
                for it in n: walk(it)
        walk(data)
    return var_map

def build_var_usage(tiles: list, var_map: Dict[str, str]) -> Dict[str, List[str]]:
    usage = {vn: [] for vn in var_map.keys()}
    for t in tiles:
        used = set()
        for q in t["queries"]:
            for vn in var_map.keys():
                if re.search(rf"(\$\{{{re.escape(vn)}\}}|\${re.escape(vn)}\b)", q):
                    used.add(vn)
        for vn in used: usage[vn].append(t["name"])
        t["vars_used"] = sorted(list(used))
    return usage

def anchor_for(name: str) -> str:
    return re.sub(r'[^a-z0-9\- ]+', '', name.lower()).replace(' ', '-')

# ----------------- DQL pretty printer -----------------

MAX_LINE = 88

def _split_on_pipes(text: str) -> str:
    """Split on | outside strings; start each pipe stage on its own line."""
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

def _split_top_level_commas(s: str) -> list:
    args, buf, lvl, in_s, qch = [], '', 0, False, ''
    for i,ch in enumerate(s):
        if in_s:
            buf += ch
            if ch == qch:
                in_s = False
            elif ch == '\\' and i+1 < len(s):
                buf += s[i+1]
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
    return args

def _wrap_func_call(name: str, arg_str: str, inner_indent: str) -> str:
    parts = _split_top_level_commas(arg_str)
    inner = (',\n' + inner_indent).join(parts)
    return f"{name}(\n{inner_indent}{inner}\n  )"

def _format_functions(text: str, force_multiline=('concat',), max_line=MAX_LINE):
    # 1) Force multiline for selected functions (concat)
    pattern = re.compile(r'(?i)\b(' + '|'.join(re.escape(n) for n in force_multiline) + r')\s*\(')
    i = 0
    s = text
    while True:
        m = pattern.search(s, i)
        if not m: break
        fn = m.group(1)
        start = m.end()-1; lvl=1; in_s=False; qch=''; j=start
        while j < len(s)-1:
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
        args = s[start+1:j]
        formatted = _wrap_func_call(fn, args, inner_indent='      ')  # 6 spaces
        s = s[:m.start()] + formatted + s[j+1:]
        i = m.start() + len(formatted)
    # 2) Wrap any overlong single-line call
    def wrap_overlong(match):
        fn, args = match.group(1), match.group(2)
        call = f"{fn}({args})"
        if len(call) <= max_line: return call
        return _wrap_func_call(fn, args, inner_indent='      ')
    s = re.sub(r'(\b[a-zA-Z_][a-zA-Z0-9_]*)\(([^()\n]*?(?:\([^)]*\)[^()]*)*?)\)', wrap_overlong, s)
    return s

def _break_keywords(text: str) -> str:
    # Newline before these, keep colon if present
    for kw in ("by:", "filter:", "fields", "timeseries", "make", "update", "select"):
        text = re.sub(rf'(?i)\s+\b{re.escape(kw)}\b', f'\n{kw}', text)
    # Newline before ' by ' and ' sort ' tokens
    text = re.sub(r'(?i)\s+\bby\b\s+', '\nby ', text)
    text = re.sub(r'(?i)\s+\bsort\b\s+', '\nsort ', text)
    return text

def _multiline_blocks(text: str) -> str:
    # timeseries and fields: split arguments by top-level commas
    def block(name: str, body: str) -> str:
        parts = _split_top_level_commas(body.strip())
        return name + '\n' + '\n'.join('  ' + p for p in parts if p)

    text = re.sub(r'(?i)\btimeseries\s+([^\n|]+)', lambda m: block('timeseries', m.group(1)), text)
    text = re.sub(r'(?i)\bfields\s+([^\n|]+)',     lambda m: block('fields',     m.group(1)), text)

    # summarize: multi-line items; stop before ' by ' if present
    def summarize_repl(m):
        tail = m.group(1)
        if ' by ' in tail:
            head, rest = tail.split(' by ', 1)
            parts = _split_top_level_commas(head)
            return 'summarize\n  ' + '\n  '.join(parts) + '\nby ' + rest
        parts = _split_top_level_commas(tail)
        return 'summarize\n  ' + '\n  '.join(parts)
    text = re.sub(r'(?i)\bsummarize\s+([^\n|]+)', summarize_repl, text)

    # filter: put condition on next lines, break on ' and ' / ' or '
    def filter_repl(m):
        cond = m.group(1).strip()
        cond = re.sub(r'(?i)\s+\band\b\s+', '\n  and ', cond)
        cond = re.sub(r'(?i)\s+\bor\b\s+',  '\n  or ',  cond)
        return 'filter:\n  ' + cond
    text = re.sub(r'(?i)\bfilter:\s*([^\n|]+)', filter_repl, text)

    return text

def format_dql_query(q: str) -> str:
    """
    Pretty-print DQL with:
      - Two-space top-level indent
      - Six-space indent for concat(...) arguments
      - Pipes on their own lines
      - Block keywords (timeseries/by:/filter:/fields) expanded and indented
      - Wrapped long function calls and multiline summarize blocks
    """
    q = q.replace("\r\n", "\n").strip()
    s = _split_on_pipes(q)
    s = _break_keywords(s)
    s = _format_functions(s, force_multiline=('concat','classicEntitySelector','in','if'))
    s = _multiline_blocks(s)

    # Final indentation pass for parentheses blocks
    lines = [ln.rstrip() for ln in s.splitlines()]
    indented, level = [], 0
    for ln in lines:
        stripped = ln.lstrip()
        if stripped.startswith((')',']','}')):
            level = max(0, level-1)
        # two-space top-level indent (except pipe lines)
        top = '' if stripped.startswith('| ') else '  '
        indented.append(top + ('  '*level) + stripped)
        opens = stripped.count('(')+stripped.count('{')+stripped.count('[')
        closes = stripped.count(')')+stripped.count('}')+stripped.count(']')
        level = max(0, level + opens - closes)
    s = '\n'.join(indented)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

# ----------------- markdown rendering -----------------

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

    # Variables
    if var_map:
        md.append("## Variables\n")
        for vn, vdql in var_map.items():
            md.append(f"### `{vn}`\n\n")
            tiles_for_var = usage.get(vn, [])
            if tiles_for_var:
                links = ", ".join(f"[{t}](#{anchor_for(t)})" for t in tiles_for_var)
                md.append(f"Used in: {links}\n\n")
            if vdql:
                md.append("```dql\n")
                md.append(format_dql_query(vdql))
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
        vars_list = " ".join(f"`{v}`" for v in t.get("vars_used", [])) or "—"
        md.append(f"| {i} | {link} | {t['type']} | {t['visualization']} | {vars_list} | {len(t['queries'])} | `{preview}` |\n")
    md.append("\n---\n\n")

    # Details
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
            md.append("```dql\n")
            md.append(pretty)
            md.append("\n```\n")
            md.append("\n</details>\n\n")
        md.append("---\n\n")
    return "".join(md)

# ----------------- main -----------------

def main():
    if len(sys.argv) < 2:
        print("Usage: extract_dt_dashboard_to_markdown_v7_3.py <dashboard.json> [output.md]", file=sys.stderr)
        sys.exit(1)

    in_path = pathlib.Path(sys.argv[1])
    out_path = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(in_path.stem + "_queries.md")

    with in_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    tiles: List[Dict[str, Any]] = []
    gather_tiles(data, ctx=["root"], acc=tiles)

    title = (data.get("dashboardMetadata", {}) or {}).get("name") or in_path.stem
    var_map = parse_variables(data)

    md = render_markdown(tiles, title, var_map)

    out_path.write_text(md, encoding="utf-8")
    print(f"Wrote Markdown with {len(tiles)} tiles -> {out_path}")

if __name__ == "__main__":
    main()
