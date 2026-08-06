#!/bin/bash
# AIOS Google Drive Automatic Sync Script
set -euo pipefail

LOG="/root/AIOS/logs/sync_gdrive.log"
mkdir -p /root/AIOS/logs
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

log "=== Google Drive Sync Started ==="

# 1. Синхронизация финансовых отчетов Excel
if [ -f "/root/AIOS/data/aios_financial_report.xlsx" ]; then
    log "📤 Загрузка финансового отчета Excel..."
    rclone copy /root/AIOS/data/aios_financial_report.xlsx gdrive:AIOS/Financial_Reports/ --update
    log "  ✅ aios_financial_report.xlsx успешно обновлен на Google Диске"
fi

# 2. Синхронизация фотокаталога запчастей
if [ -d "/root/AIOS/data/photos" ]; then
    log "📤 Синхронизация фотокаталога запчастей..."
    rclone sync /root/AIOS/data/photos/ gdrive:AIOS/Photos/ --update
    log "  ✅ Фотокаталог синхронизирован с Google Диском"
fi

# 3. Синхронизация последних свежих бэкапов (за последние 3 дня)
if [ -d "/root/AIOS/backups/daily" ]; then
    log "📤 Загрузка свежих резервных копий (бэкапов)..."
    rclone copy /root/AIOS/backups/daily/ gdrive:AIOS/Backups/ --max-age 3d --update
    log "  ✅ Свежие бэкапы загружены на Google Диск"
fi

# 4. Удаление старых бэкапов на Google Диске старше 30 дней
log "🧹 Проверка ротации старых копий на Диске (>30 дней)..."
rclone delete gdrive:AIOS/Backups/ --min-age 30d 2>>"$LOG" || true

log "=== Google Drive Sync Completed Successfully ==="
