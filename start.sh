#!/usr/bin/env bash
# Start GridSmart backend + frontend (no root npm required)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

cleanup() {
  echo ""
  echo "Stopping GridSmart..."
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# --- prerequisites ---
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required." >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "Error: npm is required." >&2
  exit 1
fi

if ! python3 -c "import fastapi, httpx, uvicorn" 2>/dev/null; then
  echo "Installing Python dependencies..."
  python3 -m pip install -r "$ROOT/backend/requirements.txt"
fi

if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd "$ROOT/frontend" && npm install)
fi

# --- configuration ---
if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
  echo "Loaded .env (ELECZ_ZONE=${ELECZ_ZONE:-US-CA-SP15})"
elif [ -f "$ROOT/.env.example" ]; then
  echo "Tip: copy .env.example to .env to set ELECZ_ZONE (e.g. DE for full 24h live prices)"
fi

export ELECZ_ZONE="${ELECZ_ZONE:-US-CA-SP15}"

# --- launch ---
echo ""
echo "GridSmart"
echo "  Frontend:  http://localhost:5173"
echo "  Backend:   http://localhost:8000"
echo "  API docs:  http://localhost:8000/docs"
echo "  Zone:      $ELECZ_ZONE"
echo ""
echo "Press Ctrl+C to stop both servers."
echo ""

(cd "$ROOT/backend" && python3 app.py) &
BACKEND_PID=$!

(cd "$ROOT/frontend" && npm run dev) &
FRONTEND_PID=$!

# Exit if either process dies
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done

echo "A server exited unexpectedly." >&2
wait || true
exit 1
