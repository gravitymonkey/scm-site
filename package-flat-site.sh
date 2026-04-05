#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_FILE="${SCRIPT_DIR}/flat-site-dist.tar.gz"

cd "$SCRIPT_DIR"

python3 build.py

rm -f "$OUTPUT_FILE"
tar -czf "$OUTPUT_FILE" -C "$SCRIPT_DIR" dist

echo "Packaged dist at: $OUTPUT_FILE"
