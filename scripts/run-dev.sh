#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

while [[ "$ROOT_DIR" != "/" ]]; do
  if [[ -f "$ROOT_DIR/backend/requirements.txt" && -f "$ROOT_DIR/frontend/package.json" ]]; then
    break
  fi
  ROOT_DIR="$(dirname "$ROOT_DIR")"
done

if [[ ! -f "$ROOT_DIR/backend/requirements.txt" || ! -f "$ROOT_DIR/frontend/package.json" ]]; then
  echo "Could not find the project root. Run this script from inside the Saltim repo."
  exit 1
fi

BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
START_DB="${START_DB:-1}"
LOAD_CSV_DATA_ON_STARTUP="${LOAD_CSV_DATA_ON_STARTUP:-1}"
BUN_BIN="${BUN_BIN:-bun}"

if ! command -v "$BUN_BIN" >/dev/null 2>&1; then
  if [[ -x "$HOME/.bun/bin/bun" ]]; then
    BUN_BIN="$HOME/.bun/bin/bun"
  else
    echo "Bun was not found. Install Bun or set BUN_BIN to the bun executable."
    exit 1
  fi
fi

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  local exit_code=$?

  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi

  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi

  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  exit "$exit_code"
}

trap cleanup EXIT INT TERM

if [[ "$START_DB" != "0" ]]; then
  echo "Starting Postgres..."
  (cd "$ROOT_DIR" && docker compose up -d db)
fi

if [[ ! -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  echo "Creating backend virtualenv..."
  python3 -m venv "$BACKEND_DIR/.venv"
fi

echo "Installing backend dependencies..."
"$BACKEND_DIR/.venv/bin/python" -m pip install -r "$BACKEND_DIR/requirements.txt"

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd "$FRONTEND_DIR" && "$BUN_BIN" install)
fi

echo "Starting backend on http://localhost:$BACKEND_PORT"
(
  cd "$BACKEND_DIR"
  LOAD_CSV_DATA_ON_STARTUP="$LOAD_CSV_DATA_ON_STARTUP" \
    .venv/bin/uvicorn app.main:app --reload --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:$FRONTEND_PORT"
(
  cd "$FRONTEND_DIR"
  "$BUN_BIN" run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

wait -n "$BACKEND_PID" "$FRONTEND_PID"
