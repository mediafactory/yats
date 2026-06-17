#!/usr/bin/env bash
#
# stop.sh — stop the local YATS test dev server started by start.sh.
#
# Matches the Django runserver process running this repo's manage.py so it
# won't touch unrelated Django projects. Pass --port N to only stop the server
# on a specific port.
set -euo pipefail

cd "$(dirname "$0")"
REPO="$(pwd)"
MANAGE="${REPO}/sites/web/manage.py"

PORT=""
for arg in "$@"; do
    case "$arg" in
        --port) shift; ;;
        --port=*) PORT="${arg#*=}" ;;
        -h|--help) echo "usage: ./stop.sh [--port N]"; exit 0 ;;
    esac
done
# support `--port N` form
if [[ "${1:-}" == "--port" && -n "${2:-}" ]]; then PORT="$2"; fi

PATTERN="$MANAGE runserver"
[[ -n "$PORT" ]] && PATTERN="$PATTERN .*:${PORT}"

PIDS="$(pgrep -f "$PATTERN" || true)"
if [[ -z "$PIDS" ]]; then
    echo "no running test server found"
    exit 0
fi

echo "stopping test server (PID: $PIDS)"
# shellcheck disable=SC2086
kill $PIDS 2>/dev/null || true
sleep 1
# force-kill any survivors
PIDS="$(pgrep -f "$PATTERN" || true)"
if [[ -n "$PIDS" ]]; then
    # shellcheck disable=SC2086
    kill -9 $PIDS 2>/dev/null || true
fi
echo "stopped"
