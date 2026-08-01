#!/bin/bash
# AIOS automatic backup
# Backs up SQLite DBs (via .backup for consistency) + data dirs into backups/daily
# Keeps last $KEEP days. Run daily via cron.

set -euo pipefail

DATE=$(date +%Y%m%d_%H%M%S)
BK="/root/AIOS/backups/daily"
KEEP=${KEEP_DAYS:-14}
mkdir -p "$BK"
LOG="/root/AIOS/logs/backup.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

log "=== Backup start ==="

# --- SQLite databases (consistent backup via sqlite3 .backup) ---
declare -A DBS
DBS[/root/AIOS/data/aios.sqlite]="aios.sqlite"
DBS[/root/AIOS/data/olx_http.sqlite]="olx_http.sqlite"
DBS[/root/AIOS/data/olx_subs.sqlite]="olx_subs.sqlite"
DBS[/root/AIOS/data/profiles.sqlite]="profiles.sqlite"
DBS[/root/AIOS/data/devices.sqlite]="devices.sqlite"
DBS[/root/AIOS/data/shards.sqlite]="shards.sqlite"
# container volume copy
DBS[/var/lib/docker/volumes/aios_aios-data/_data/aios.sqlite]="docker_aios.sqlite"

for db in "${!DBS[@]}"; do
  name="${DBS[$db]}"
  if [ -f "$db" ]; then
    out="$BK/${DATE}__${name}"
    if sqlite3 "$db" ".backup '$out'" 2>>"$LOG"; then
      log "  OK $name ($(stat -c%s "$out" 2>/dev/null || echo 0) bytes)"
    else
      log "  FAIL $name ($db)"
    fi
  else
    log "  SKIP (not found) $db"
  fi
done

# --- Data directories ---
TARBALL="$BK/${DATE}__data.tar.gz"
if tar -czf "$TARBALL" \
   -C /root/AIOS \
   data 2>/dev/null; then
  # exclude sqlite which are already backed individually? keep simple: only json/config
  log "  OK data dir tarball"
fi

# --- Chroma DB ---
CHROMA="$BK/${DATE}__chroma.tar.gz"
if tar -czf "$CHROMA" -C /root/AIOS chroma_db 2>/dev/null; then
  log "  OK chroma_db tarball"
fi

# --- Rotate: delete old backups ---
DEL=$(find "$BK" -type f -mtime +"$KEEP" -delete 2>>"$LOG" | wc -l)
log "  Rotation: removed old files > ${KEEP}d"

# --- Summary ---
TOTAL=$(du -sh "$BK" 2>/dev/null | awk '{print $1}')
log "Backup complete. Total: $TOTAL"
echo "Backup OK -> $BK (total $TOTAL)"
