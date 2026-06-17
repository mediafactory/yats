#!/usr/bin/env bash
#
# start.sh — spin up a local YATS test environment (SQLite, no Docker).
#
# Idempotent: safe to re-run. It
#   1. creates a Python venv under testenv/.venv and installs deps,
#   2. compiles the Tailwind CSS (downloads the standalone CLI once),
#   3. migrates a SQLite DB under testenv/data/,
#   4. loads demo data from vagrant/init_db.json (first run only),
#   5. collects static files and starts the Django dev server.
#
# Config: testenv/test.ini (SQLite + local paths)
# Settings: testenv/test_settings.py (LocMem cache + Haystack simple backend,
#           so neither memcached nor native Xapian are required).
#
# Env overrides: HOST (default 127.0.0.1), PORT (default 8000),
#                PYTHON (python interpreter to build the venv with).
set -euo pipefail

cd "$(dirname "$0")"
REPO="$(pwd)"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
VENV="${REPO}/testenv/.venv"
DATA="${REPO}/testenv/data"
INI="${REPO}/testenv/test.ini"
PY_BIN="${VENV}/bin/python"
MANAGE="${REPO}/sites/web/manage.py"

export YATS_CONFIG="$INI"
export DJANGO_SETTINGS_MODULE="test_settings"
# modules/ holds the apps, sites/web/ holds the project + manage.py,
# testenv/ holds test_settings.py
export PYTHONPATH="${REPO}/modules:${REPO}/sites/web:${REPO}/testenv"

log() { printf '\n=== %s ===\n' "$*"; }

# ---- pick a python ----
choose_python() {
    if [[ -n "${PYTHON:-}" ]]; then echo "$PYTHON"; return; fi
    for c in python3.12 python3.11 python3; do
        if command -v "$c" >/dev/null 2>&1; then echo "$c"; return; fi
    done
    echo "python3"
}

log "directories"
mkdir -p "${DATA}/db" "${DATA}/logs" "${DATA}/files" "${DATA}/tmp" "${DATA}/static" "${DATA}/index"

log "virtualenv"
if [[ ! -x "$PY_BIN" ]]; then
    BASE_PY="$(choose_python)"
    echo "creating venv with $BASE_PY ($($BASE_PY --version 2>&1))"
    "$BASE_PY" -m venv "$VENV"
fi
"$PY_BIN" -m pip install --quiet --upgrade pip
"$PY_BIN" -m pip install --quiet -r "${REPO}/testenv/requirements.txt"

log "tailwind css"
TW_VERSION="v3.4.17"
TW_BIN="${REPO}/.bin/tailwindcss"
if [[ ! -x "$TW_BIN" ]]; then
    mkdir -p "${REPO}/.bin"
    case "$(uname -s)-$(uname -m)" in
        Darwin-arm64) TW_ASSET="tailwindcss-macos-arm64" ;;
        Darwin-x86_64) TW_ASSET="tailwindcss-macos-x64" ;;
        Linux-aarch64) TW_ASSET="tailwindcss-linux-arm64" ;;
        *) TW_ASSET="tailwindcss-linux-x64" ;;
    esac
    echo "downloading $TW_ASSET"
    curl -fsSL -o "$TW_BIN" \
        "https://github.com/tailwindlabs/tailwindcss/releases/download/${TW_VERSION}/${TW_ASSET}"
    chmod +x "$TW_BIN"
fi
"$TW_BIN" -i "${REPO}/assets/tailwind.input.css" -o "${REPO}/modules/yats/static/tailwind.css" --minify

log "migrate"
"$PY_BIN" "$MANAGE" migrate --noinput

# ---- demo data (first run only) ----
FRESH_MARKER="${DATA}/.fixtures_loaded"
if [[ ! -f "$FRESH_MARKER" ]]; then
    log "load demo data (vagrant/init_db.json)"
    if "$PY_BIN" "$MANAGE" loaddata "${REPO}/vagrant/init_db.json"; then
        touch "$FRESH_MARKER"
        echo "demo data loaded. login: admin / admin"
    else
        echo "WARNING: fixture load failed — continuing with an empty DB" >&2
    fi
else
    echo "demo data already loaded (delete ${FRESH_MARKER} to reload)"
fi

log "collectstatic"
"$PY_BIN" "$MANAGE" collectstatic --noinput >/dev/null

log "runserver http://${HOST}:${PORT}/"
echo "login at http://${HOST}:${PORT}/local_login/  (user: admin)"
exec "$PY_BIN" "$MANAGE" runserver "${HOST}:${PORT}"
