#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-9405}"

cd "$SCRIPT_DIR"

python3 build.py

echo "Serving flat-site/dist at http://localhost:${PORT}"
exec python3 -m http.server "$PORT" --directory "$SCRIPT_DIR/dist"
