#!/usr/bin/env bash
# Stop FlavorPilot with SIGTERM, then SIGKILL only if a process is still alive.

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

forced=0
stopped=0

echo "Stopping FlavorPilot..."

command_matches() {
  local pid="$1"
  local command
  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [[ "$command" == *"backend.app.main"* || "$command" == *"python -m app.main"* || "$command" == *" app.main"* || "$command" == *"vite"* || "$command" == *"npm run dev"* ]]
}

graceful_stop() {
  local pid="$1"
  local label="$2"
  local require_match="${3:-1}"
  if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
    return 1
  fi
  if [[ "$require_match" -eq 1 ]] && ! command_matches "$pid"; then
    echo "   Skipping pid ${pid}; it is not a FlavorPilot process."
    return 1
  fi
  local pgid
  pgid="$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d '[:space:]')"
  echo "   Sending SIGTERM to ${label} (${pid})."
  if [[ -n "$pgid" ]]; then
    kill -TERM -"$pgid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
  else
    kill -TERM "$pid" 2>/dev/null || true
  fi
  local _
  for _ in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "   ${label} exited after SIGTERM."
      stopped=1
      return 0
    fi
    sleep 0.25
  done
  echo "   ${label} is still running. Sending SIGKILL."
  if [[ -n "$pgid" ]]; then
    kill -KILL -"$pgid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
  else
    kill -KILL "$pid" 2>/dev/null || true
  fi
  forced=1
  stopped=1
  return 0
}

stop_pidfile() {
  local name="$1"
  local file="$ROOT/.flavorpilot.${name}.pid"
  if [[ ! -f "$file" ]]; then
    return 1
  fi
  local pid
  pid="$(tr -d '[:space:]' <"$file")"
  graceful_stop "$pid" "$name" || true
  rm -f "$file"
}

stop_port() {
  local port="$1"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  local pid
  for pid in $pids; do
    graceful_stop "$pid" "port ${port}" 0 || true
  done
}

stop_pidfile backend
stop_pidfile frontend
stop_port 8000
stop_port 8080
stop_port 5173

if [[ "$stopped" -eq 0 ]]; then
  echo "   No FlavorPilot processes found."
fi
echo ""
if [[ "$forced" -eq 1 ]]; then
  echo "FlavorPilot stopped, but one process needed SIGKILL."
  exit 1
fi
echo "FlavorPilot stopped."
echo ""
