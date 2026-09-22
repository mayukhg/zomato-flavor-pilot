#!/usr/bin/env bash
# Start FlavorPilot and record the process-group leaders so stop.sh can
# shut both servers down with SIGTERM.

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
mkdir -p "$ROOT/.run"

echo "Starting FlavorPilot..."

if command -v pg_isready >/dev/null 2>&1 && pg_isready -h localhost -q >/dev/null 2>&1; then
  echo "PostgreSQL is accepting connections."
  if command -v psql >/dev/null 2>&1; then
    psql -h localhost -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'flavorpilot'" 2>/dev/null | grep -q 1 \
      || psql -h localhost -U postgres -c "CREATE DATABASE flavorpilot" >/dev/null 2>&1 \
      || echo "Could not create the flavorpilot database. Continuing."
  fi
else
  echo "PostgreSQL is not running. The API will start, and database writes will fail until it is up."
fi

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="$(command -v python3 || command -v python || true)"
fi
if [[ -z "${PY}" ]]; then
  echo "Python was not found."
  exit 1
fi

launch() {
  local name="$1"
  shift
  python3 -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' "$@" \
    >"$ROOT/.run/${name}.log" 2>&1 &
  echo $! >"$ROOT/.flavorpilot.${name}.pid"
  echo "   ${name} pid $(cat "$ROOT/.flavorpilot.${name}.pid")"
}

echo "Starting the API..."
launch backend "$PY" -m backend.app.main

echo "Starting the frontend..."
launch frontend npm run dev

echo "Waiting for the API and the frontend..."
backend_ready=0
frontend_ready=0
frontend_url="http://localhost:8080"
for _ in $(seq 1 40); do
  if [[ "$backend_ready" -eq 0 ]] && curl -sf "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    backend_ready=1
  fi
  if [[ "$frontend_ready" -eq 0 ]]; then
    if curl -sf "http://127.0.0.1:8080" >/dev/null 2>&1; then
      frontend_ready=1
      frontend_url="http://localhost:8080"
    elif curl -sf "http://127.0.0.1:5173" >/dev/null 2>&1; then
      frontend_ready=1
      frontend_url="http://localhost:5173"
    fi
  fi
  if [[ "$backend_ready" -eq 1 && "$frontend_ready" -eq 1 ]]; then
    break
  fi
  sleep 0.5
done

echo ""
if [[ "$backend_ready" -eq 1 && "$frontend_ready" -eq 1 ]]; then
  echo "FlavorPilot is running."
else
  echo "FlavorPilot did not finish starting. See .run/backend.log and .run/frontend.log."
fi
echo "   Frontend:    ${frontend_url}"
echo "   Backend API: http://localhost:8000"
echo "   API docs:    http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

cleanup() {
  "$ROOT/stop.sh"
  exit 0
}
trap cleanup INT TERM

wait
