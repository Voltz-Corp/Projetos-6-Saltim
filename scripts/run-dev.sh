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
START_MLFLOW="${START_MLFLOW:-1}"
START_MAILPIT="${START_MAILPIT:-1}"
LOAD_CSV_DATA_ON_STARTUP="${LOAD_CSV_DATA_ON_STARTUP:-1}"
SMTP_HOST="${SMTP_HOST:-localhost}"
SMTP_PORT="${SMTP_PORT:-1025}"
SMTP_FROM_EMAIL="${SMTP_FROM_EMAIL:-pedidos@saltim.local}"
SMTP_FROM_NAME="${SMTP_FROM_NAME:-Saltim Cafe}"
SMTP_USE_TLS="${SMTP_USE_TLS:-0}"
BUN_BIN="${BUN_BIN:-bun}"
DOCKER_BIN="${DOCKER_BIN:-docker}"

is_wsl() {
  [[ -f /proc/version ]] && grep -qi microsoft /proc/version
}

find_python() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
  elif command -v python >/dev/null 2>&1; then
    command -v python
  elif command -v py >/dev/null 2>&1; then
    command -v py
  else
    return 1
  fi
}

venv_python_path() {
  if [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
    echo "$BACKEND_DIR/.venv/bin/python"
  elif [[ -x "$BACKEND_DIR/.venv/Scripts/python.exe" ]]; then
    echo "$BACKEND_DIR/.venv/Scripts/python.exe"
  else
    echo ""
  fi
}

docker_compose() {
  (cd "$ROOT_DIR" && "$DOCKER_BIN" compose "$@")
}

wait_for_service_health() {
  local service="$1"
  local container_id
  local status

  container_id="$(docker_compose ps -q "$service")"
  if [[ -z "$container_id" ]]; then
    return 0
  fi

  for _ in {1..60}; do
    status="$("$DOCKER_BIN" inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$container_id" 2>/dev/null || true)"
    case "$status" in
      healthy|no-healthcheck) return 0 ;;
      unhealthy)
        echo "Service $service is unhealthy."
        return 1
        ;;
    esac
    sleep 1
  done

  echo "Timed out waiting for $service to be healthy."
  return 1
}

if ! command -v "$BUN_BIN" >/dev/null 2>&1; then
  if [[ -x "$HOME/.bun/bin/bun" ]]; then
    BUN_BIN="$HOME/.bun/bin/bun"
  else
    echo "Bun was not found. Install Bun or set BUN_BIN to the bun executable."
    exit 1
  fi
fi

if [[ "$START_DB" != "0" || "$START_MLFLOW" != "0" || "$START_MAILPIT" != "0" ]]; then
  if ! command -v "$DOCKER_BIN" >/dev/null 2>&1; then
    if is_wsl && command -v docker.exe >/dev/null 2>&1; then
      DOCKER_BIN="$(command -v docker.exe)"
    elif is_wsl && [[ -x "/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe" ]]; then
      DOCKER_BIN="/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"
    else
      echo "Docker was not found."
      echo "Install Docker Desktop and enable WSL integration, or set DOCKER_BIN to the Docker executable."
      exit 1
    fi
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
  docker_compose up -d db
  wait_for_service_health db
fi

if [[ "$START_MLFLOW" != "0" ]]; then
  echo "Starting MLflow..."
  docker_compose up -d mlflow
fi

if [[ "$START_MAILPIT" != "0" ]]; then
  echo "Starting Mailpit..."
  docker_compose up -d mailpit
  echo "Mailpit inbox: http://localhost:8025"
fi

BACKEND_PYTHON="$(venv_python_path)"
if [[ -z "$BACKEND_PYTHON" ]]; then
  PYTHON_BIN="$(find_python || true)"
  if [[ -z "$PYTHON_BIN" ]]; then
    echo "Python was not found. Install Python 3.11+ or add it to PATH."
    exit 1
  fi

  echo "Creating backend virtualenv..."
  if [[ "$(basename "$PYTHON_BIN")" == "py" || "$(basename "$PYTHON_BIN")" == "py.exe" ]]; then
    "$PYTHON_BIN" -3 -m venv "$BACKEND_DIR/.venv"
  else
    "$PYTHON_BIN" -m venv "$BACKEND_DIR/.venv"
  fi
  BACKEND_PYTHON="$(venv_python_path)"
fi

echo "Installing backend dependencies..."
"$BACKEND_PYTHON" -m pip install -r "$BACKEND_DIR/requirements.txt"

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd "$FRONTEND_DIR" && "$BUN_BIN" install)
fi

echo "Starting backend on http://localhost:$BACKEND_PORT"
(
  cd "$BACKEND_DIR"
  LOAD_CSV_DATA_ON_STARTUP="$LOAD_CSV_DATA_ON_STARTUP" \
    SMTP_HOST="$SMTP_HOST" \
    SMTP_PORT="$SMTP_PORT" \
    SMTP_FROM_EMAIL="$SMTP_FROM_EMAIL" \
    SMTP_FROM_NAME="$SMTP_FROM_NAME" \
    SMTP_USE_TLS="$SMTP_USE_TLS" \
    "$BACKEND_PYTHON" -m uvicorn app.main:app --reload --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:$FRONTEND_PORT"
(
  cd "$FRONTEND_DIR"
  "$BUN_BIN" run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

echo ""
echo "Saltim is running:"
echo "  Frontend: http://localhost:$FRONTEND_PORT"
echo "  Backend:  http://localhost:$BACKEND_PORT"
echo "  API docs: http://localhost:$BACKEND_PORT/docs"
if [[ "$START_MAILPIT" != "0" ]]; then
  echo "  Emails:   http://localhost:8025"
fi
if [[ "$START_MLFLOW" != "0" ]]; then
  echo "  MLflow:   http://localhost:5000"
fi
echo ""

wait -n "$BACKEND_PID" "$FRONTEND_PID"
