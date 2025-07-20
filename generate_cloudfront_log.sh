#!/bin/bash
# cloudfront_log_generator.sh

# Define output location
OUTPUT_DIR="./cloudfront_logs"
mkdir -p $OUTPUT_DIR

# Write Python script inline
cat << EOF > $OUTPUT_DIR/generate_cloudfront_log.py
import os
import random
import gzip
from datetime import datetime

FIELDS = [
    'date', 'time', 'x-edge-location', 'sc-bytes', 'c-ip', 'cs-method', 'cs(Host)', 'cs-uri-stem', 'sc-status',
    'cs(Referer)', 'cs(User-Agent)', 'cs-uri-query', 'cs(Cookie)', 'x-edge-result-type', 'x-edge-request-id',
    'x-host-header', 'cs-protocol', 'cs-bytes', 'time-taken', 'x-forwarded-for', 'ssl-protocol', 'ssl-cipher',
    'x-edge-response-result-type', 'cs-protocol-version', 'fle-status', 'fle-encrypted-fields', 'c-port',
    'time-to-first-byte', 'x-edge-detailed-result-type', 'sc-content-type', 'sc-content-len',
    'sc-range-start', 'sc-range-end'
]

LOCATIONS = ['LAX1', 'ORD2', 'IAD2', 'DFW3', 'CDG5', 'SIN3']
METHODS = ['GET', 'POST']
HOSTS = ['d1suky0192j3i4.cloudfront.net']
URIS = ['/', '/favicon.ico', '/index.html', '/products', '/api/data']
STATUSES = ['200', '301', '403', '404', '500']
REFERERS = ['-', 'https://example.com/', 'https://google.com', 'https://mysite.net/']
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'Chrome/137.0.0.0 Safari/537.36'
]
PROTOCOLS = ['https', 'http']
CIPHERS = ['TLS_AES_128_GCM_SHA256', 'TLS_AES_256_GCM_SHA384']

def generate_log_line():
    now = datetime.utcnow()
    return "\t".join([
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S"),
        random.choice(LOCATIONS),
        str(random.randint(100, 10000)),
        f"{random.randint(10, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}",
        random.choice(METHODS),
        random.choice(HOSTS),
        random.choice(URIS),
        random.choice(STATUSES),
        random.choice(REFERERS),
        random.choice(USER_AGENTS),
        "-", "-", random.choice(["Hit", "Miss", "Error"]),
        "ZyxQ4C==",
        "eligibleapi-service-tool.lifeaat.test.ic1.statefarm",
        random.choice(PROTOCOLS),
        str(random.randint(100, 2000)),
        f"{round(random.uniform(0.01, 0.5), 3)}",
        "-", "TLSv1.3",
        random.choice(CIPHERS),
        random.choice(["Hit", "Miss", "Error"]),
        "HTTP/2.0", "-", "-",
        str(random.randint(10000, 20000)),
        f"{round(random.uniform(0.01, 0.5), 3)}",
        random.choice(["Miss", "Error"]),
        "application/xml",
        str(random.randint(100, 3000)),
        "-", "-"
    ])

lines = [generate_log_line() for _ in range(random.randint(10, 20))]
filename = f"E3ROY2EOWK4DDV.{datetime.utcnow().strftime('%Y-%m-%d-%H.%M.%S')}.log.gz"
filepath = os.path.join("./cloudfront_logs", filename)

with gzip.open(filepath, 'wt') as f:
    for line in lines:
        f.write(line + "\n")

print(f"Generated {filepath}")
EOF

# Run the Python script
python3 $OUTPUT_DIR/generate_cloudfront_log.py
