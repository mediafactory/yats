#!/usr/bin/env bash
#
# update.sh — update OS + YATS app on mf-yats-1 and restart all webs.
# Idempotent. Run as root.
#
# Optional env: APP_DIR YATS_USER SITES BRANCH SKIP_OS=1
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/yats}"
YATS_USER="${YATS_USER:-yats}"
SITES="${SITES:-mf bagarino schiwago}"
BRANCH="${BRANCH:-develop}"
SKIP_OS="${SKIP_OS:-0}"
VENV="${APP_DIR}/.venv"
PY="${VENV}/bin/python"

log() { printf '\n=== %s ===\n' "$*"; }
[[ $EUID -eq 0 ]] || { echo "run as root" >&2; exit 1; }

run_manage() { # site, args...
    local site="$1"; shift
    sudo -u "$YATS_USER" \
        env DJANGO_SETTINGS_MODULE=web.settings \
            YATS_CONFIG="/etc/yats/${site}.ini" \
            PYTHONPATH="${APP_DIR}/modules:${APP_DIR}/sites/web" \
        "$PY" "${APP_DIR}/sites/web/manage.py" "$@"
}

if [[ "$SKIP_OS" != "1" ]]; then
    log "OS packages"
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get -y upgrade
fi

log "app code ($BRANCH)"
git -C "$APP_DIR" fetch --prune origin
git -C "$APP_DIR" checkout "$BRANCH"
git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
chown -R "$YATS_USER:$YATS_USER" "$APP_DIR"

log "python deps"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install --upgrade -r "${APP_DIR}/deploy/requirements.txt"

log "systemd units (in case they changed)"
install -m 0644 "${APP_DIR}/deploy/systemd/yats-web@.service"   /etc/systemd/system/yats-web@.service
install -m 0644 "${APP_DIR}/deploy/systemd/yats-tasks@.service" /etc/systemd/system/yats-tasks@.service
systemctl daemon-reload

log "translations (once)"
first="$(echo "$SITES" | awk '{print $1}')"
run_manage "$first" compilemessages

for site in $SITES; do
    log "update web: $site"
    run_manage "$site" migrate --noinput
    run_manage "$site" collectstatic --noinput
    run_manage "$site" update_index --remove --age 24 || run_manage "$site" update_index
    systemctl restart "yats-web@${site}.service" "yats-tasks@${site}.service"
done

log "health check"
sleep 3
for site in $SITES; do
    bind="$(sed -n 's/^GUNICORN_BIND=//p' "/etc/yats/${site}.env")"
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://${bind}/" || echo 000)"
    printf '  %-10s %s -> HTTP %s\n' "$site" "$bind" "$code"
done
echo "update done."
