#!/usr/bin/env bash
# Start backend + frontend together (no root npm required)
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  echo ""
  echo "Stopping GridSmart..."
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting backend on http://localhost:8000"
(cd "$ROOT/backend" && python3 app.py) &

echo "Starting frontend on http://localhost:5173"
(cd "$ROOT/frontend" && npm run dev) &

wait
