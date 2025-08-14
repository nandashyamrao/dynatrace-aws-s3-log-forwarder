# Dynatrace Dashboard Query & Description Extractor

This file contains **two approaches** to extract all `Query` and `Description` values from a Dynatrace dashboard JSON export, even if the JSON contains lots of escaped characters or nested/encoded strings.

---

## 1️⃣ Python Script (Robust, Handles Double-Escaped JSON)

Save as `extract_dt_dashboard_queries.py`:

```python
#!/usr/bin/env python3
import sys, json, pathlib, csv
from typing import Any, Dict, List, Tuple, Union

Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

QUERY_KEYS = {
    "query", "dql", "ql",
    "metricSelector", "metricExpression", "metricExpressions",
    "metric"
}
DESC_KEYS = {"description", "tileDescription", "markdown", "notes"}
NAME_KEYS = {"name", "title", "customName", "displayName", "tileType"}

def try_json_decode(value: str) -> Any:
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
            if k.lower() in QUERY_KEYS or k.lower() in {"value", "expression"}:
                out.extend(normalize_query_value(v))
            if isinstance(v, dict) and "string" in v and k.lower() in QUERY_KEYS:
                out.extend(normalize_query_value(v["string"]))
        for k in ("query", "dql", "ql"):
            if k in val:
                out.extend(normalize_query_value(val[k]))
    return [s for s in (q.strip() for q in out) if s]

def walk(node: Json, ctx: List[str], results: List[Tuple[str, str, str]]):
    local_desc: List[str] = []

    if isinstance(node, dict):
        for nk in NAME_KEYS:
            if nk in node and isinstance(node[nk], str):
                name_val = node[nk].strip()
                if name_val and (not ctx or name_val != ctx[-1]):
                    ctx = ctx + [name_val]
                break

        for dk in DESC_KEYS:
            if dk in node and isinstance(node[dk], str):
                desc = node[dk].strip()
                if desc:
                    local_desc.append(desc)

        collected_queries: List[str] = []
        for qk in QUERY_KEYS:
            if qk in node:
                collected_queries.extend(normalize_query_value(node[qk]))
        if "queries" in node:
            collected_queries.extend(normalize_query_value(node["queries"]))

        if collected_queries:
            desc_joined = " | ".join(local_desc) if local_desc else ""
            for q in collected_queries:
                results.append((" / ".join(ctx), desc_joined, q))

        for k, v in node.items():
            walk(v, ctx + [k], results)

    elif isinstance(node, list):
        for idx, item in enumerate(node):
            walk(item, ctx + [f"[{idx}]"], results)

def main():
    if len(sys.argv) < 2:
        print("Usage: extract_dt_dashboard_queries.py <dashboard.json> [output.csv]", file=sys.stderr)
        sys.exit(1)

    in_path = pathlib.Path(sys.argv[1])
    out_path = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else None

    with in_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    results: List[Tuple[str, str, str]] = []
    walk(data, ctx=["root"], results=results)

    seen = set()
    deduped = []
    for row in results:
        if row not in seen:
            seen.add(row)
            deduped.append(row)

    if out_path:
        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ContextPath", "Description", "Query"])
            w.writerows(deduped)
        print(f"Wrote {len(deduped)} rows → {out_path}")
    else:
        print(f"Found {len(deduped)} query rows\n")
        for ctx, desc, qry in deduped:
            print("—"*80)
            print(f"Context   : {ctx}")
            if desc:
                print(f"Description: {desc}")
            print("Query     :")
            print(qry)

if __name__ == "__main__":
    main()
```

---

## 2️⃣ Shell / jq Version

This version uses `jq` to parse and optionally decode escaped JSON inside the file.

```bash
jq -r '
def dejson:
  (.|fromjson? // .)
  | (.|fromjson? // .);

def grab($k):
  .. | objects | select(has($k)) | .[$k] | dejson
  | if type=="array" or type=="object" then . else tostring end;

def first_desc:
  (grab("description") // grab("tileDescription") // grab("markdown") // grab("notes"));

def queries:
  [ grab("query"), grab("dql"), grab("ql"), grab("metricSelector"), grab("metricExpression"), grab("metricExpressions") ]
  | map( if type=="array" then .[] else . end )
  | map(tostring)
  | map(select(length>0));

def context:
  [ (.. | objects | (.name? // .title? // .customName? // .displayName?) // empty | tostring) ][0];

[
  (paths | select(length>0)) as $p
  | (getpath($p)) as $n
  | ($n | type) as $t
  | if ($t=="object" and
        ( ["query","dql","ql","metricSelector","metricExpression","metricExpressions"]
          | any(.; has(.) as $h | $h) ))
    then
      (context // "N/A") as $ctx
      | (first_desc // "") as $desc
      | (queries) as $qs
      | $qs[] | [$ctx, $desc, .]
    else empty end
] | .[]
| @tsv
' my_dashboard.json
```
