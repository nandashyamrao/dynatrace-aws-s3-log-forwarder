#!/usr/bin/env bash
set -euo pipefail

INPUT="${1:-}"
OUTPUT="${2:-}"
BAD_ROWS="${3:-bad_rows.csv}"

if [[ -z "${INPUT}" || -z "${OUTPUT}" ]]; then
  echo "Usage: $0 input.csv output.csv [bad_rows.csv]"
  exit 1
fi

# Start clean
: > "${OUTPUT}"
: > "${BAD_ROWS}"

awk -v OUT="${OUTPUT}" -v BAD="${BAD_ROWS}" '
# -----------------------------
# Quote-aware CSV line parser
# -----------------------------
function parse_csv_line(line, out,    i,c,field,inside,n) {
  n = 0
  field = ""
  inside = 0

  for (i = 1; i <= length(line); i++) {
    c = substr(line, i, 1)

    if (c == "\"") {
      # Handle escaped quotes ("")
      if (inside && i < length(line) && substr(line, i + 1, 1) == "\"") {
        field = field "\""
        i++
      } else {
        inside = !inside
        field = field c
      }
    } else if (c == "," && !inside) {
      n++
      out[n] = field
      field = ""
    } else {
      field = field c
    }
  }

  n++
  out[n] = field
  return n
}

# -----------------------------
# Field cleanup rules (your logic)
# -----------------------------
function fix_field(f, idx,    t, clean_t) {
  t = f
  sub(/^[ \t\r\n]+/, "", t)
  sub(/[ \t\r\n]+$/, "", t)

  # Column 1 example: NULL/blank -> NA, strip quotes for numeric
  if (idx == 1) {
    if (t == "" || t == "\"\"" || tolower(t) == "null") return "NA"
    if (t ~ /^"[0-9]+"$/) { sub(/^"/, "", t); sub(/"$/, "", t) }
    return t
  }

  # Column 6 example: product_name handling
  if (idx == 6) {
    clean_t = t
    gsub(/^"+/, "", clean_t)
    gsub(/"+$/, "", clean_t)
    sub(/^[ \t\r\n]+/, "", clean_t)
    sub(/[ \t\r\n]+$/, "", clean_t)

    if (clean_t == "" || tolower(clean_t) == "null") return "NA"
    if (t ~ /^".*"$/) { sub(/^"/, "", t); sub(/"$/, "", t) }
    return t
  }

  if (t == "" || t == "\"\"" || tolower(t) == "null") return "NA"
  return f
}

# -----------------------------
# Helpers: write bad row
# BAD format: reason,line_number,raw_row
# (raw row is double-quoted and internal quotes doubled)
# -----------------------------
function write_bad(reason, line_no, raw,    esc) {
  esc = raw
  gsub(/"/, "\"\"", esc)       # escape quotes for CSV
  printf "\"%s\",%d,\"%s\"\n", reason, line_no, esc >> BAD
  bad_count++
}

BEGIN {
  good_count = 0
  bad_count = 0
  expected = -1

  # Write bad_rows header
  print "\"reason\",\"line_number\",\"raw_row\"" >> BAD
}

{
  rawline = $0

  # Guard: even number of quotes on the line
  qc = gsub(/"/, "&", rawline)
  if (qc % 2 != 0) {
    write_bad("UNBALANCED_QUOTES", NR, rawline)
    next
  }

  # Header row defines expected column count
  if (NR == 1) {
    expected = parse_csv_line(rawline, hdr)
    print rawline >> OUT  # header preserved exactly
    next
  }

  # Parse row + enforce canonical column count
  n = parse_csv_line(rawline, raw)

  if (n != expected) {
    write_bad("COLUMN_MISMATCH (found " n " expected " expected ")", NR, rawline)
    next
  }

  # Clean fields then rebuild line
  for (i = 1; i <= n; i++) {
    fields[i] = fix_field(raw[i], i)
  }

  # Final safety pass: whitespace-only -> NA
  for (i = 1; i <= n; i++) {
    tmp = fields[i]
    sub(/^[ \t\r\n]+/, "", tmp)
    sub(/[ \t\r\n]+$/, "", tmp)
    if (tmp == "") fields[i] = "NA"
  }

  # Print rebuilt CSV row
  for (i = 1; i <= n; i++) {
    printf "%s%s", fields[i], (i < n ? "," : ORS) >> OUT
  }

  good_count++
}

END {
  # stderr summary so it shows in CI logs
  print "Detected header columns: " expected > "/dev/stderr"
  print "Good rows written: " good_count > "/dev/stderr"
  print "Bad rows quarantined: " bad_count > "/dev/stderr"
  print "Bad rows file: " BAD > "/dev/stderr"
}
' "${INPUT}"

echo "✅ Wrote cleaned CSV to: ${OUTPUT}"
echo "⚠️  Quarantined bad rows to: ${BAD_ROWS}"
