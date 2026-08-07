#!/bin/bash
set -euo pipefail
LOG=/root/AIOS/logs/disk_cleanup_manual.log
mkdir -p /root/AIOS/logs
{
  echo "=== $(date -Is) disk cleanup ==="
  df -h /
  # old daily backups > 14d
  if [ -d /root/AIOS/backups/daily ]; then
    find /root/AIOS/backups/daily -type f -mtime +14 -print -delete || true
  fi
  # tmp aios artifacts
  find /tmp -maxdepth 1 -type f \( -name 'aios_*' -o -name 'xvfb-run.*' -o -name 'core.*' \) -mtime +2 -print -delete 2>/dev/null || true
  # old logs rotated
  find /root/AIOS/logs -type f -name '*.log.*' -mtime +14 -print -delete 2>/dev/null || true
  find /root/AIOS/logs -type f -name '*.log' -size +50M -exec truncate -s 5M {} \; -print 2>/dev/null || true
  # pycache
  find /root/AIOS -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
  # chrome twin old screenshots if huge
  if [ -d /root/AIOS/data/chrome_twin ]; then
    find /root/AIOS/data/chrome_twin -type f \( -name '*.png' -o -name '*.jpg' \) -mtime +21 -print -delete 2>/dev/null || true
  fi
  # docker prune dangling (safe)
  docker image prune -f >/dev/null 2>&1 || true
  journalctl --vacuum-time=7d >/dev/null 2>&1 || true
  echo "after:"
  df -h /
  du -sh /root/AIOS/backups /root/AIOS/data /tmp 2>/dev/null || true
} | tee -a "$LOG"
