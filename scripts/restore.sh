#!/usr/bin/env sh
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: restore.sh <backup_file.sql[.gz]>"
  exit 1
fi

FILE="$1"
echo "[restore] Restoring $FILE to $POSTGRES_DB"
if echo "$FILE" | grep -q ".gz$"; then
  gunzip -c "$FILE" | psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" "$POSTGRES_DB"
else
  psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" "$POSTGRES_DB" < "$FILE"
fi
echo "[restore] Done"

