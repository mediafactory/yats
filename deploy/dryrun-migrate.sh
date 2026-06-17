#!/usr/bin/env bash
#
# dryrun-migrate.sh — de-risk the schema migration BEFORE the live cutover.
#
# The 3 old web DBs and this repo have divergent 'web'-app migration histories
# (different auto-migration names after web.0003). They are all AlterField-only
# (no new columns) and the model is identical everywhere, so `migrate` should be
# effectively a no-op for those — but verify per DB first.
#
# Run on mf-yats-1 (has venv + repo + /etc/yats/<site>.ini). Run as the yats user.
#
#   ./dryrun-migrate.sh mf              # safe: shows `migrate --plan` (read-only)
#   SCRATCH=1 SCRATCH_SUFFIX=_dry ./dryrun-migrate.sh mf
#                                       # full: clone prod DB -> scratch, migrate it
#
# SCRATCH mode needs a DB user allowed to CREATE DATABASE on the cluster and
# pg_dump/psql in PATH. It NEVER touches the production DB.
set -euo pipefail

SITE="${1:?usage: dryrun-migrate.sh <site>}"
APP_DIR="${APP_DIR:-/opt/yats}"
INI="/etc/yats/${SITE}.ini"
PY="${APP_DIR}/.venv/bin/python"
MANAGE="${APP_DIR}/sites/web/manage.py"
export DJANGO_SETTINGS_MODULE=web.settings
export PYTHONPATH="${APP_DIR}/modules:${APP_DIR}/sites/web"

[[ -f "$INI" ]] || { echo "missing $INI" >&2; exit 1; }

# read DB params from the INI (no secrets echoed)
read_ini() { "$PY" - "$INI" "$1" <<'PYEOF'
import configparser,sys
c=configparser.ConfigParser(interpolation=None); c.read(sys.argv[1])
print(c.get('database', sys.argv[2], fallback=''))
PYEOF
}
DB_NAME="$(read_ini DATABASE_NAME)"; DB_USER="$(read_ini DATABASE_USER)"
DB_HOST="$(read_ini DATABASE_HOST)"; DB_PORT="$(read_ini DATABASE_PORT)"
DB_PASS="$(read_ini DATABASE_PASSWORD)"

echo "### migrate --plan (READ-ONLY) for $SITE [$DB_NAME@$DB_HOST] ###"
YATS_CONFIG="$INI" "$PY" "$MANAGE" migrate --plan

if [[ "${SCRATCH:-0}" != "1" ]]; then
    echo
    echo "Read-only plan shown. To actually test applying on a COPY: SCRATCH=1 $0 $SITE"
    exit 0
fi

SCRATCH_DB="${DB_NAME}${SCRATCH_SUFFIX:-_dryrun}"
export PGPASSWORD="$DB_PASS"
echo "### cloning $DB_NAME -> $SCRATCH_DB on $DB_HOST ###"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$SCRATCH_DB\";"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$SCRATCH_DB\" TEMPLATE template0;"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$SCRATCH_DB"

# temp INI pointing at the scratch DB
TMP_INI="$(mktemp /tmp/yats-dry-XXXX.ini)"; trap 'rm -f "$TMP_INI"' EXIT
sed "s/^DATABASE_NAME:.*/DATABASE_NAME: ${SCRATCH_DB}/" "$INI" > "$TMP_INI"

echo "### migrate (on scratch copy) ###"
YATS_CONFIG="$TMP_INI" "$PY" "$MANAGE" migrate --noinput
echo "### makemigrations --check (drift?) ###"
YATS_CONFIG="$TMP_INI" "$PY" "$MANAGE" makemigrations --check --dry-run || true
echo
echo "Dry-run done. Inspect output above. Drop the scratch DB when finished:"
echo "  PGPASSWORD=... psql -h $DB_HOST -U $DB_USER -d postgres -c 'DROP DATABASE \"$SCRATCH_DB\";'"
