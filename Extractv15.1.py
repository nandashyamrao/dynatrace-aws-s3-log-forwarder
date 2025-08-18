#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynatrace Dashboard -> Markdown extractor (v15.1)

What’s new
- Adds a “View in Dynatrace” link under the title that points to the original dashboard.
- Link can be constructed two ways:
  1) Pass --ui-origin https://<tenant>.apps.dynatrace.com (or set DT_UI_ORIGIN),
     and we’ll form:
       {ui_origin}/ui/apps/dynatrace.dashboards/dashboard/{dashboard_id}
  2) Pass --id-url-map dashboards.csv (columns: id,url) to map ids to full links.

Usage
  python3 extract_dashboards.py [--ui-origin https://...apps.dynatrace.com]
                                [--id-url-map dashboards.csv]

  (Runs in the current directory; processes all *.json and writes “*_TileQueries.md”)
"""
import sys, json, pathlib, datetime, re, csv, argparse, os
from typing import Any, Dict, List, Union, Tuple

Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

QUERY_KEYS = {"query","dql","ql","metricSelector","metricExpression","metricExpressions","metric"}
DESC_KEYS  = {"description","tileDescription","markdown","notes"}
NAME_KEYS  = {"name","title","customName","displayName"}
TYPE_KEYS  = {"tileType","type"}

# ---------------- basic helpers ----------------

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
            s = decoded.strip(); continue
        return decoded
    return s

def normalize_query_value(val: Any) -> List[str]:
    out: List[str] = []
    val = try_json_decode(val)
    if isinstance(val, str):
        out.append(val)
    elif isinstance(val, list):
        for it in val: out.extend(normalize_query_value(it))
    elif isinstance(val, dict):
        for k,v in val.items():
            kl = k.lower()
            if kl in QUERY_KEYS or kl in {"value","expression"}:
                out.extend(normalize_query_value(v))
            if isinstance(v, dict) and "string" in v and kl in QUERY_KEYS:
                out.extend(normalize_query_value(v["string"]))
        for k in ("query","dql","ql"):
            if k in val: out.extend(normalize_query_value(val[k]))
    return [s for s in (q.strip() for q in out) if s]

def unique(items: List[str]) -> List[str]:
    seen, out = set(), []
    for x in items:
        if x not in seen:
            seen.add(x); out.append(x)
    return out

def get_nested(d: Dict[str, Any], path: List[str]):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur: cur = cur[p]
        else: return None
    return cur

def detect_visualization(node: Dict[str, Any]) -> str:
    c = []
    v = get_nested(node, ["visualConfig","type"])
    if isinstance(v, str) and v.strip(): c.append(v.strip())
    for k in ("visualization","viz","chartType","graphType"):
        vv = node.get(k)
        if isinstance(vv, str) and vv.strip(): c.append(vv.strip())
    if not c and isinstance(node.get("visualConfig"), dict):
        for k,vv in node["visualConfig"].items():
            if isinstance(vv,str) and vv.strip() and k.lower() in ("visualization","type","charttype","graphtype"):
                c.append(vv.strip())
    return c[0] if c else "—"

def gather_tiles(node: Json, ctx: List[str], acc: List[Dict[str, Any]]):
    if isinstance(node, dict):
        display = next((node[k].strip() for k in NAME_KEYS if isinstance(node.get(k),str) and node[k].strip()), None)
        tile_type = next((node[k].strip() for k in TYPE_KEYS if isinstance(node.get(k),str) and node[k].strip()), None)
        descs: List[str] = []
        for dk in DESC_KEYS:
            if isinstance(node.get(dk),str) and node[dk].strip():
                descs.append(node[dk].strip())
        queries: List[str] = []
        for qk in QUERY_KEYS:
            if qk in node: queries.extend(normalize_query_value(node[qk]))
        if "queries" in node: queries.extend(normalize_query_value(node["queries"]))
        if queries:
            acc.append({
                "context": " / ".join(ctx),
                "name": display or "Dashboard Spacer Cell",
                "type": tile_type or "—",
                "visualization": detect_visualization(node),
                "description": " | ".join(descs) if descs else "",
                "queries": unique(queries),
            })
        for k,v in node.items():
            gather_tiles(v, ctx+[k], acc)
    elif isinstance(node, list):
        for i,it in enumerate(node):
            gather_tiles(it, ctx+[f"[{i}]"], acc)

def first_line(s: str, maxlen: int=96) -> str:
    fl = s.splitlines()[0].strip()
    return (fl[:maxlen]+"…") if len(fl)>maxlen else fl

# -------- Variables (support 'input') --------

DQL_HINTS = ("fetch ","| filter"," filter ","summarize","timeseries","lookup","join","parse")
VAR_VALUE_KEYS = ("input","query","dql","definition","data","string","value","expression")

def looks_like_dql(text: str) -> bool:
    t = text.strip().lower()
    return any(h in t for h in DQL_HINTS)

def extract_dql_from_obj(obj: Dict[str, Any]) -> str:
    for key in VAR_VALUE_KEYS:
        val = obj.get(key)
        if isinstance(val, str) and looks_like_dql(val): return val.strip()
        if isinstance(val, dict):
            for kk in VAR_VALUE_KEYS:
                vv = val.get(kk)
                if isinstance(vv, str) and looks_like_dql(vv): return vv.strip()
    for v in obj.values():
        if isinstance(v, str) and looks_like_dql(v): return v.strip()
        if isinstance(v, dict):
            for vv in v.values():
                if isinstance(vv, str) and looks_like_dql(vv): return vv.strip()
    return ""

def parse_variables(data: Dict[str, Any]) -> Dict[str,str]:
    var_map: Dict[str,str] = {}
    def add_var(name: str, dql: str):
        if not name: return
        name = name.strip().strip("${} ")
        if not name: return
        var_map.setdefault(name, dql.strip() if dql else "")
    containers = []
    for path in (["variables"], ["dashboardMetadata","variables"], ["inputs"]):
        node = get_nested(data,path)
        if isinstance(node,list): containers.append(node)
    for arr in containers:
        for v in arr:
            if isinstance(v,dict):
                name = v.get("name") or v.get("key") or v.get("id")
                add_var(name, extract_dql_from_obj(v))
    if not var_map:
        def walk(n: Json):
            if isinstance(n,dict):
                name = n.get("name") or n.get("key") or n.get("id")
                if isinstance(name,str) and name.strip():
                    dql = extract_dql_from_obj(n)
                    if dql: add_var(name,dql)
                for vv in n.values(): walk(vv)
            elif isinstance(n,list):
                for it in n: walk(it)
        walk(data)
    return var_map

def build_var_usage(tiles: List[Dict[str,Any]], var_map: Dict[str,str]) -> Dict[str,List[str]]:
    usage = {vn: [] for vn in var_map}
    for t in tiles:
        used=set()
        for q in t["queries"]:
            for vn in var_map:
                if re.search(rf"(\$\{{{re.escape(vn)}\}}|\${re.escape(vn)}\b)", q):
                    used.add(vn)
        for vn in used: usage[vn].append(t["name"])
        t["vars_used"]=sorted(list(used))
    return usage

def anchor_for(name: str) -> str:
    return re.sub(r'[^a-z0-9\- ]+', '', name.lower()).replace(' ','-')

# -------- Simple DQL pretty (gentle; preserves logic) --------

def format_dql_query(q: str) -> str:
    q = q.replace("\r\n","\n").strip()
    # avoid splitting commented pipe lines (// ...)
    out, buf, i, in_str, qch = [], "", 0, False, ""
    while i < len(q):
        ch = q[i]
        nxt = q[i+1] if i+1<len(q) else ""
        if in_str:
            buf += ch
            if ch == qch:
                in_str = False
            elif ch == "\\" and i+1<len(q):
                buf += q[i+1]; i+=1
        else:
            if ch in ('"',"'"):
                in_str=True; qch=ch; buf+=ch
            elif ch == '|' and not buf.strip().startswith('//'):
                out.append(buf.strip()); buf="| "
            else:
                buf+=ch
        i+=1
    out.append(buf.strip())
    s = "\n".join(part if part.startswith("| ") else part for part in out if part.strip())
    # lightly wrap concat(...) if extremely long
    s = re.sub(r'\bconcat\(([^()\n]{80,})\)',
               lambda m: "concat(\n      " + ",\n      ".join([a.strip() for a in m.group(1).split(",")]) + "\n  )",
               s, flags=re.I)
    return s

# -------- Dashboard link helpers --------

def load_id_url_map(path: Union[str, None]) -> Dict[str,str]:
    if not path: return {}
    p = pathlib.Path(path)
    if not p.exists(): return {}
    mapping={}
    with p.open("r", encoding="utf-8-sig") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            i = (row.get("id") or "").strip()
            u = (row.get("url") or "").strip()
            if i and u: mapping[i]=u
    return mapping

def dashboard_id_from_json(data: Dict[str,Any]) -> str:
    # common locations
    if isinstance(data.get("id"), str): return data["id"]
    mid = get_nested(data, ["dashboardMetadata","id"])
    if isinstance(mid, str): return mid
    return ""

def build_dashboard_url(dashboard_id: str, ui_origin: str) -> str:
    if not dashboard_id or not ui_origin: return ""
    return f"{ui_origin.rstrip('/')}/ui/apps/dynatrace.dashboards/dashboard/{dashboard_id}"

# -------- Markdown rendering --------

def render_markdown(tiles, title: str, var_map: Dict[str,str], dash_url: str) -> str:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    total_q = sum(len(t["queries"]) for t in tiles)
    tiles_sorted = sorted(tiles, key=lambda t: (t["name"]=="Dashboard Spacer Cell", t["name"].lower()))
    usage = build_var_usage(tiles_sorted, var_map)

    md=[]
    md.append(f"# {title} — Tile Query Details\n\n")
    md.append(f"_Generated on {ts}. Tiles with queries: **{len(tiles_sorted)}**. Total queries: **{total_q}**._\n\n")
    if dash_url:
        md.append(f"**Original dashboard:** [{title}]({dash_url})\n\n")
    if var_map:
        md.append(f"**Detected dashboard variables:** {' '.join(f'`{v}`' for v in var_map)}\n\n")
    md.append("---\n\n")

    if var_map:
        md.append("## Variables\n\n")
        for vn, vdql in var_map.items():
            md.append(f"### `{vn}`\n\n")
            tiles_for_var = usage.get(vn,[])
            if tiles_for_var:
                links = ", ".join(f"[{t}](#{anchor_for(t)})" for t in tiles_for_var)
                md.append(f"Used in: {links}\n\n")
            if vdql:
                md.append(f"```sql\n{format_dql_query(vdql)}\n```\n\n")
            else:
                md.append("_Definition not found in export._\n\n")
        md.append("---\n\n")

    md.append("## Overview\n")
    md.append("| # | Tile | Type | Visualization | Vars Used | Queries | Preview |\n|---:|---|---|---|---|---:|---|\n")
    for i,t in enumerate(tiles_sorted,1):
        link=f"[{t['name']}](#{anchor_for(t['name'])})"
        preview=first_line(t["queries"][0]) if t["queries"] else ""
        vars_list=" ".join(f"`{v}`" for v in t.get("vars_used", [])) or "—"
        md.append(f"| {i} | {link} | {t['type']} | {t['visualization']} | {vars_list} | {len(t['queries'])} | `{preview}` |\n")
    md.append("\n---\n\n")

    for t in tiles_sorted:
        md.append(f"## {t['name']}\n\n")
        md.append(f"**Type:** `{t['type']}`  \n**Visualization:** `{t['visualization']}`  \n**Context:** `{t['context']}`\n\n")
        if t.get("vars_used"):
            md.append("**Vars Used:** " + ", ".join(f"`{v}`" for v in t["vars_used"]) + "\n\n")
        if t["description"]:
            md.append("> " + t["description"].replace("\n","\n> ") + "\n\n")
        for qi,q in enumerate(t["queries"],1):
            pretty = format_dql_query(q)
            lines = len(pretty.splitlines())
            md.append(f"<details>\n<summary><strong>Query {qi}</strong> — {lines} line{'s' if lines!=1 else ''}</summary>\n\n```sql\n{pretty}\n```\n\n</details>\n\n")
        md.append("---\n\n")
    return "".join(md)

# -------- main --------

def main():
    ap = argparse.ArgumentParser(description="Extract Dynatrace dashboard JSON -> Markdown with links")
    ap.add_argument("--ui-origin", default=os.environ.get("DT_UI_ORIGIN","").strip(),
                    help="e.g. https://ecf94088.apps.dynatrace.com (used to build live dashboard link)")
    ap.add_argument("--id-url-map", default="", help="CSV with columns id,url to map dashboard ids to full links")
    args = ap.parse_args()

    id_url_map = load_id_url_map(args.id_url_map) if args.id_url_map else {}

    for in_path in sorted(pathlib.Path(".").glob("*.json")):
        with in_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        tiles: List[Dict[str,Any]] = []
        gather_tiles(data, ctx=["root"], acc=tiles)

        title = (data.get("dashboardMetadata", {}) or {}).get("name") or in_path.stem
        dash_id = dashboard_id_from_json(data)
        dash_url = id_url_map.get(dash_id) or build_dashboard_url(dash_id, args.ui_origin)

        var_map = parse_variables(data)
        _ = build_var_usage(tiles, var_map)  # annotate vars_used

        out_path = pathlib.Path(f"{in_path.stem}_TileQueries.md")
        md = render_markdown(tiles, title, var_map, dash_url)
        out_path.write_text(md, encoding="utf-8")
        print(f"Wrote {out_path} (linked: {'yes' if dash_url else 'no'})")

if __name__ == "__main__":
    main()
