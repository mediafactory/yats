#!/usr/bin/env bash
#
# bootstrap.sh — install the YATS application for 3 webs on mf-yats-1.
# Idempotent: safe to re-run. Run as root.
#
# DB-dependent steps (migrate / update_index / start) are deferred to the
# cutover by default (the cluster DB creds must be filled into the INIs and the
# old app stopped first). Set RUN_DB_STEPS=1 to also run them — see MIGRATION.md.
#
# Required: PRIVATE_IP=<this server's Hetzner private IP> (gunicorn bind addr).
# Optional env: REPO_URL BRANCH APP_DIR YATS_USER SITES RUN_DB_STEPS
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/mediafactory/yats.git}"
BRANCH="${BRANCH:-develop}"
APP_DIR="${APP_DIR:-/opt/yats}"
YATS_USER="${YATS_USER:-yats}"
SITES="${SITES:-mf bagarino schiwago}"
PRIVATE_IP="${PRIVATE_IP:-}"
RUN_DB_STEPS="${RUN_DB_STEPS:-0}"
VENV="${APP_DIR}/.venv"
PY="${VENV}/bin/python"
declare -A PORTS=( [mf]=8001 [bagarino]=8002 [schiwago]=8003 )

log() { printf '\n=== %s ===\n' "$*"; }
[[ $EUID -eq 0 ]] || { echo "run as root" >&2; exit 1; }
[[ -n "$PRIVATE_IP" ]] || { echo "set PRIVATE_IP=<hetzner private ip>" >&2; exit 1; }

log "service user"
getent group "$YATS_USER" >/dev/null || groupadd --system "$YATS_USER"
id "$YATS_USER" >/dev/null 2>&1 || \
    useradd --system --gid "$YATS_USER" --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$YATS_USER"

if [[ "${SKIP_GIT:-0}" == "1" ]]; then
    log "repository: SKIP_GIT=1 — using code already present in ${APP_DIR}"
    [[ -d "$APP_DIR" ]] || { echo "SKIP_GIT set but ${APP_DIR} is missing" >&2; exit 1; }
else
    log "repository ($BRANCH)"
    if [[ -d "${APP_DIR}/.git" ]]; then
        git -C "$APP_DIR" fetch --prune origin
        git -C "$APP_DIR" checkout "$BRANCH"
        git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
    else
        git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
    fi
fi
chown -R "$YATS_USER:$YATS_USER" "$APP_DIR"

log "virtualenv (--system-site-packages for apt Xapian)"
[[ -d "$VENV" ]] || python3 -m venv --system-site-packages "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "${APP_DIR}/deploy/requirements.txt"

log "put modules + web on the venv path"
SP="$("$PY" -c 'import site; print(site.getsitepackages()[0])')"
printf '%s\n%s\n' "${APP_DIR}/modules" "${APP_DIR}/sites/web" > "${SP}/yats.pth"

log "systemd units + sudoers"
install -m 0644 "${APP_DIR}/deploy/systemd/yats-web@.service"   /etc/systemd/system/yats-web@.service
install -m 0644 "${APP_DIR}/deploy/systemd/yats-tasks@.service" /etc/systemd/system/yats-tasks@.service
install -m 0440 -o root -g root "${APP_DIR}/deploy/sudoers.d/yats-signal" /etc/sudoers.d/yats-signal
visudo -cf /etc/sudoers.d/yats-signal
systemctl daemon-reload

log "signal-cli"
SITES="$SITES" YATS_USER="$YATS_USER" bash "${APP_DIR}/deploy/install-signal-cli.sh"

log "per-web config, dirs, services"
install -d -m 0755 -o root -g root /etc/yats
for site in $SITES; do
    for d in files static logs index; do
        install -d -m 0750 -o "$YATS_USER" -g "$YATS_USER" "/var/web/${site}/${d}"
    done

    # gunicorn bind (deployment-specific)
    umask 027
    printf 'GUNICORN_BIND=%s:%s\n' "$PRIVATE_IP" "${PORTS[$site]:-8000}" > "/etc/yats/${site}.env"
    chown root:"$YATS_USER" "/etc/yats/${site}.env"; chmod 0640 "/etc/yats/${site}.env"

    # INI from template (only if absent, to preserve filled-in secrets/DB creds)
    if [[ ! -f "/etc/yats/${site}.ini" ]]; then
        secret="$("$PY" -c 'import secrets; print(secrets.token_urlsafe(50))')"
        "$PY" - "$site" "$secret" \
            "${APP_DIR}/deploy/etc-yats/web.ini.template" "/etc/yats/${site}.ini" <<'PYEOF'
import sys
site, secret, tmpl, out = sys.argv[1:5]
text = open(tmpl).read()
repl = {
    '@SITE@': site,
    '@DOMAIN@': f'{site}.mediafactory.de',
    '@PROJECT_NAME@': site,
    '@SECRET_KEY@': secret,
    '@SERVER_EMAIL@': 'tickets@mediafactory.de',
    '@ADMINS@': '',
    # DB cluster creds — fill before the cutover (see MIGRATION.md):
    '@DB_NAME@': 'CHANGEME', '@DB_USER@': 'CHANGEME', '@DB_PASSWORD@': 'CHANGEME',
    '@DB_HOST@': 'CHANGEME', '@DB_PORT@': '5432',
    # signal number — fill after registration (see signal/register.md):
    '@SIGNAL_NUMBER@': '',
}
for k, v in repl.items():
    text = text.replace(k, v)
open(out, 'w').write(text)
PYEOF
        chown root:"$YATS_USER" "/etc/yats/${site}.ini"; chmod 0640 "/etc/yats/${site}.ini"
        echo "  -> NEW /etc/yats/${site}.ini — fill DB_* (cluster) + SIGNAL number"
    fi
    umask 022

    systemctl enable "yats-web@${site}.service" "yats-tasks@${site}.service" >/dev/null
done

run_manage() { # site, args...
    local site="$1"; shift
    sudo -u "$YATS_USER" \
        env DJANGO_SETTINGS_MODULE=web.settings \
            YATS_CONFIG="/etc/yats/${site}.ini" \
            PYTHONPATH="${APP_DIR}/modules:${APP_DIR}/sites/web" \
        "$PY" "${APP_DIR}/sites/web/manage.py" "$@"
}

log "compile translations (once; app-level .mo files)"
first="$(echo "$SITES" | awk '{print $1}')"
# compilemessages must run inside a tree that has locale/ (the yats module).
sudo -u "$YATS_USER" sh -c "cd '${APP_DIR}/modules/yats' && \
    DJANGO_SETTINGS_MODULE=web.settings YATS_CONFIG='/etc/yats/${first}.ini' \
    PYTHONPATH='${APP_DIR}/modules:${APP_DIR}/sites/web' \
    '${PY}' '${APP_DIR}/sites/web/manage.py' compilemessages"

log "collectstatic per web (no DB needed)"
for site in $SITES; do run_manage "$site" collectstatic --noinput; done

if [[ "$RUN_DB_STEPS" == "1" ]]; then
    log "DB steps (migrate + index) + start — cutover mode"
    for site in $SITES; do
        run_manage "$site" migrate --noinput
        run_manage "$site" clear_index --noinput
        run_manage "$site" update_index   # haystack update_index takes no --noinput
        systemctl restart "yats-web@${site}.service" "yats-tasks@${site}.service"
    done
else
    cat <<EOF

Bootstrap finished (install/config only). Next:
  1) Fill DB cluster creds + SIGNAL number into /etc/yats/<site>.ini
  2) Register signal numbers          -> deploy/signal/register.md
  3) Run the cutover (migrate + start) -> deploy/MIGRATION.md
     (or re-run with RUN_DB_STEPS=1 once INIs are complete and old app is stopped)
EOF
fi
