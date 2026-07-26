#!/bin/sh
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
if [ -n "$DATABASE_URL" ]; then
    pg_dump "$DATABASE_URL" | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"
fi
tar -czf "$BACKUP_DIR/data_$TIMESTAMP.tar.gz" -C /app data/ 2>/dev/null || true
find "$BACKUP_DIR" -type f -mtime +7 -delete
echo "Backup done: $TIMESTAMP"
