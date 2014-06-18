#!/bin/bash
 
USER="postgres" 
 
PSQL="$(which psql)"
#PSQL="/Library/PostgreSQL/9.1/bin/psql"
PG_DUMP="$(which pg_dump)"
#PG_DUMP="/Library/PostgreSQL/9.1/bin/pg_dump"
CHOWN="$(which chown)"
CHMOD="$(which chmod)"
GZIP="$(which gzip)"

DEST="/backup"
LOGFILE="$DEST/log/logfile.log"
LOGDIR="$DEST/log/" 
 
HOST="$(hostname)"
 
NOW="$(date +"%d%m%Y_%H%M")"

MBD="$DEST/postgresql"
databases=("schiwago" "schiwago_test" "tryton" "tryton_test")

[ ! -d $MBD ] && mkdir -p $MBD || :
[ ! -d $LOGDIR ] && mkdir -p $LOGDIR || :
 
# Only root
#$CHOWN 0.0 -R $DEST
#$CHMOD 0600 $DEST
 
tLen=${#databases[@]}
for (( i=0; i<${tLen}; i++ )); do
#	echo "Starting at `date` for database: ${databases[$i]} " >> $LOGFILE 2>&1
#	$PSQL -c "vacuum verbose analyze" -d ${databases[$i]} -U $USER >> $LOGFILE 2>&1
	$PG_DUMP ${databases[$i]} -h 127.0.0.1  -U $USER -w --format tar --blobs --encoding UTF8 | $GZIP > "$MBD/${databases[$i]}-$NOW-backup.gz"
pg_dump: reading schemas
done
