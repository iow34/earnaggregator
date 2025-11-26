#!/usr/bin/env sh
set -euo pipefail

DATE="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="/backups"
mkdir -p "$BACKUP_DIR"

echo "[backup] Starting PostgreSQL backup at $DATE"
pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > "$BACKUP_DIR/pg_${POSTGRES_DB}_${DATE}.sql.gz"
echo "[backup] Done: $BACKUP_DIR/pg_${POSTGRES_DB}_${DATE}.sql.gz"

