#!/bin/bash

# ---------------- CONFIG ----------------
SRC_DIR="./cloudfront_logs"
BUCKET="dts3fwdsns"
PREFIX="cloudfront/807080909195/eligibleapi"
LOG_COUNT=100
# ----------------------------------------

mkdir -p "$SRC_DIR"

echo "📁 Generating CloudFront logs in: $SRC_DIR"

python3 - <<EOF
import os
import random
import gzip
from datetime import datetime, timedelta

output_dir = "$SRC_DIR"
os.makedirs(output_dir, exist_ok=True)

LOG_COUNT = $LOG_COUNT
FIELDS = "#Version: 1.0\n#Fields: date time x-edge-location sc-bytes c-ip cs-method cs(Host) cs-uri-stem cs(Referer) cs(User-Agent) cs-uri-query\n"

EDGE_LOCATIONS = ['LAX3', 'ORD5', 'IAD2', 'DFW3', 'CDG5', 'SIN3']
METHODS = ['GET', 'POST']
URIS = ['/favicon.ico', '/index.html', '/products', '/api/data', '/contact', '/cart']
STATUSES = ['200', '302', '403', '404', '500']
REFERERS = ['-', 'https://example.com', 'https://google.com', 'https://mysite.net']
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Amazon CloudFront",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
]

def generate_log_line(log_date):
    time = log_date.strftime('%H:%M:%S')
    date = log_date.strftime('%Y-%m-%d')
    location = random.choice(EDGE_LOCATIONS)
    bytes_sent = str(random.randint(1000, 50000))
    ip = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
    method = random.choice(METHODS)
    host = "d123.cloudfront.net"
    uri = random.choice(URIS)
    status = random.choice(STATUSES)
    referer = random.choice(REFERERS)
    agent = random.choice(USER_AGENTS)
    uri_query = "id=abc123&session=xyz"

    return f"{date} {time} {location} {bytes_sent} {ip} {method} {host} {uri} {status} {referer} {agent} {uri_query}\n"

base_time = datetime.utcnow()

for i in range(LOG_COUNT):
    timestamp = base_time + timedelta(minutes=i)
    filename = os.path.join(output_dir, f"cloudfront_log_{timestamp.strftime('%Y%m%dT%H%M%SZ')}.gz")
    with gzip.open(filename, "wt") as f:
        f.write(FIELDS)
        for _ in range(random.randint(5, 15)):
            f.write(generate_log_line(timestamp))
    print(f"📝 Created log: {filename}")
EOF

# ---------------- Upload to S3 ----------------
echo "☁️ Uploading generated logs to: s3://$BUCKET/$PREFIX"

for file in "$SRC_DIR"/*.gz; do
  if [[ -f "$file" ]]; then
    filename=$(basename "$file")
    aws s3 cp "$file" "s3://$BUCKET/$PREFIX/$filename"
    if [[ $? -eq 0 ]]; then
      echo "✅ Uploaded: $filename"
    else
      echo "❌ Failed to upload: $filename"
    fi
  fi
done
