#!/usr/bin/env python3
"""
Dynatrace Dashboard -> Markdown extractor (v15)

Features:
- Reads all JSON files in the current folder.
- Generates <jsonfile>_TileQueries.md for each.
- Title: "<JsonFileName> - Tile Query Details".
- Variables section: includes variable definitions and tiles where used.
- Overview: compact 4-column table.
- Pretty DQL formatting with indentation.
- Keeps comments intact: `//` lines are not broken at pipes.
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
    if not isinstance(value, str): return value
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
        for item in val: out.extend(normalize_query_value(item))
    elif isinstance(val, dict):
        for k, v in val.items():
            if k.lower() in QUERY_KEYS or k.lower() in {"value", "expression"}:
                out.extend(normalize_query_value(v))
        for k in ("query","dql","ql"):
            if k in val: out.extend(normalize_query_value(val[k]))
    return [s for s in (q.strip() for q in out) if s]

def get_nested(d: Dict[str, Any], path: List[str]):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur: cur = cur[p]
        else: return None
    return cur

def detect_visualization(node: Dict[str, Any]) -> str:
    v = get_nested(node, ["visualConfig","type"])
    if isinstance(v,str) and v.strip(): return v.strip()
    for k in ("visualization","viz","chartType","graphType"):
        vv = node.get(k)
        if isinstance(vv,str) and vv.strip(): return vv.strip()
    return "—"

def gather_tiles(node: Json, ctx: List[str], acc: List[Dict[str,Any]]):
    if isinstance(node, dict):
        display = next((node[nk].strip() for nk in NAME_KEYS if nk in node and isinstance(node[nk],str) and node[nk].strip()), None)
        tile_type = next((node[tk].strip() for tk in TYPE_KEYS if tk in node and isinstance(node[tk],str) and node[tk].strip()), None)
        descs = [node[dk].strip() for dk in DESC_KEYS if dk in node and isinstance(node[dk],str) and node[dk].strip()]
        queries = []
        for qk in QUERY_KEYS:
            if qk in node: queries.extend(normalize_query_value(node[qk]))
        if "queries" in node: queries.extend(normalize_query_value(node["queries"]))
        if queries:
            acc.append({
                "context":" / ".join(ctx),
                "name":display or "Dashboard Spacer Cell",
                "type":tile_type or "—",
                "visualization":detect_visualization(node),
                "description":" | ".join(descs) if descs else "",
                "queries":list(dict.fromkeys(queries))
            })
        for k,v in node.items(): gather_tiles(v, ctx+[k], acc)
    elif isinstance(node, list):
        for i,item in enumerate(node): gather_tiles(item, ctx+[f"[{i}]"], acc)

# -------- Variables --------
DQL_HINTS = ("fetch ","filter ","| filter","summarize","timeseries","lookup","join","parse")
VAR_KEYS = ("input","query","dql","definition","data","string","value","expression")

def looks_like_dql(text:str)->bool:
    t=text.strip().lower(); return any(h in t for h in DQL_HINTS)

def extract_dql_from_obj(obj:Dict[str,Any])->str:
    for k in VAR_KEYS:
        v=obj.get(k)
        if isinstance(v,str) and looks_like_dql(v): return v.strip()
        if isinstance(v,dict):
            for kk in VAR_KEYS:
                vv=v.get(kk)
                if isinstance(vv,str) and looks_like_dql(vv): return vv.strip()
    return ""

def parse_variables(data:Dict[str,Any])->Dict[str,str]:
    out={}
    for path in (["variables"],["dashboardMetadata","variables"],["inputs"]):
        node=get_nested(data,path)
        if isinstance(node,list):
            for v in node:
                if isinstance(v,dict):
                    name=v.get("name") or v.get("key") or v.get("id")
                    dql=extract_dql_from_obj(v)
                    if name: out[name]=dql
    return out

def build_var_usage(tiles:List[Dict[str,Any]], var_map:Dict[str,str])->Dict[str,List[str]]:
    usage={vn:[] for vn in var_map}
    for t in tiles:
        used=set()
        for q in t["queries"]:
            for vn in var_map:
                if re.search(rf"(\$\{{{re.escape(vn)}\}}|\${re.escape(vn)}\b)",q): used.add(vn)
        for vn in used: usage[vn].append(t["name"])
        t["vars_used"]=sorted(list(used))
    return usage

def anchor_for(name:str)->str:
    return re.sub(r'[^a-z0-9\- ]+','',name.lower()).replace(' ','-')

# -------- DQL Formatter --------
def format_dql_query(q:str)->str:
    q=q.replace("\r\n","\n").strip()
    lines=[]
    buf=""
    in_str=False; qch=""
    for i,ch in enumerate(q):
        if in_str:
            buf+=ch
            if ch==qch: in_str=False
            elif ch=="\\" and i+1<len(q): buf+=q[i+1]
            continue
        if ch in ("'","\""):
            in_str=True; qch=ch; buf+=ch; continue
        if ch=="|" and not buf.strip().startswith("//"):
            lines.append(buf.strip()); buf="| "
        else: buf+=ch
    if buf.strip(): lines.append(buf.strip())
    return "\n".join(lines)

# -------- Markdown --------
def render_markdown(tiles,title:str,var_map:Dict[str,str])->str:
    ts=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    usage=build_var_usage(tiles,var_map)
    md=[]
    md.append(f"# {title}\n\n_Generated on {ts}_\n\n")
    if var_map:
        md.append("## Variables\n\n")
        md.append("| Variable | Used In Tiles | Definition |\n|---|---|---|\n")
        for vn,dql in var_map.items():
            used=", ".join(f"[{t}](#{anchor_for(t)})" for t in usage.get(vn,[])) or "—"
            defn=f"```sql\n{format_dql_query(dql)}\n```" if dql else "_not found_"
            md.append(f"| `{vn}` | {used} | {defn} |\n")
        md.append("\n---\n\n")
    md.append("## Overview\n\n")
    md.append("| Tile | Type | Visualization | Vars Used |\n|---|---|---|---|\n")
    for t in tiles:
        link=f"[{t['name']}](#{anchor_for(t['name'])})"
        vars_used=" ".join(f"`{v}`" for v in t.get("vars_used",[])) or "—"
        md.append(f"| {link} | {t['type']} | {t['visualization']} | {vars_used} |\n")
    md.append("\n---\n\n")
    for t in tiles:
        md.append(f"## {t['name']}\n\n")
        md.append(f"**Type:** `{t['type']}`  \n**Visualization:** `{t['visualization']}`  \n**Context:** `{t['context']}`\n\n")
        if t.get("vars_used"): md.append("**Vars Used:** "+", ".join(f"`{v}`" for v in t["vars_used"])+"\n\n")
        if t["description"]: md.append("> "+t["description"]+"\n\n")
        for qi,q in enumerate(t["queries"],1):
            pretty=format_dql_query(q)
            md.append(f"<details>\n<summary><strong>Query {qi}</strong></summary>\n\n```sql\n{pretty}\n```\n\n</details>\n\n")
        md.append("---\n\n")
    return "".join(md)

# -------- main --------
def main():
    for in_path in pathlib.Path(".").glob("*.json"):
        with in_path.open(encoding="utf-8") as f: data=json.load(f)
        tiles=[]; gather_tiles(data,["root"],tiles)
        title=f"{in_path.stem} - Tile Query Details"
        var_map=parse_variables(data)
        md=render_markdown(tiles,title,var_map)
        out_path=in_path.with_name(in_path.stem+"_TileQueries.md")
        out_path.write_text(md,encoding="utf-8")
        print(f"Wrote {out_path}")

if __name__=="__main__": main()
