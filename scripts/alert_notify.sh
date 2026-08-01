#!/bin/bash
# AIOS alert notifier: polls Prometheus for firing alerts and sends to Telegram.
# Reads Telegram credentials from /etc/aios/aios-auto-coder.env (root-only).
# Run every minute via cron. Avoids duplicate sends by tracking last fired set.
set -uo pipefail

PROM="http://127.0.0.1:9090"
# Load secrets from env file (no secrets hardcoded here)
if [ -f /etc/aios/aios-auto-coder.env ]; then
  export $(grep -E "^(AIOS_TELEGRAM_TOKEN|TELEGRAM_CHAT_ID)=" /etc/aios/aios-auto-coder.env | xargs)
fi
TOKEN="${AIOS_TELEGRAM_TOKEN:-}"
CHAT="${TELEGRAM_CHAT_ID:-}"
STATE="/root/AIOS/data/metrics_exporter/.alerts_state"
mkdir -p "$(dirname "$STATE")"

if [ -z "$TOKEN" ] || [ -z "$CHAT" ]; then
  echo "[alert_notify] missing AIOS_TELEGRAM_TOKEN or TELEGRAM_CHAT_ID" >> /root/AIOS/logs/alert_notify.log
  exit 0
fi

CURRENT=$("$PROM/api/v1/alerts" 2>/dev/null | /usr/bin/python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
except Exception:
    sys.exit(0)
for a in d.get('data',{}).get('alerts',[]):
    if a.get('state')=='firing':
        lab=a.get('labels',{})
        print(lab.get('alertname','?'))
")
CURRENT=$(printf '%s\n' "$CURRENT" | grep -v "^$" | sort -u)

[ -f "$STATE" ] && PREV=$(cat "$STATE") || PREV=""
PREV=$(printf '%s\n' "$PREV" | grep -v "^$" | sort -u)

NEW=$(comm -23 <(printf '%s\n' "$CURRENT") <(printf '%s\n' "$PREV") | grep -v "^$")

if [ -n "$NEW" ]; then
  MSG="⚠️ AIOS Alert"
  while IFS= read -r a; do
    [ -z "$a" ] && continue
    MSG="${MSG}
• $a"
  done <<< "$NEW"
  curl -s -m 10 "https://api.telegram.org/bot$TOKEN/sendMessage" \
    --data-urlencode "chat_id=$CHAT" \
    --data-urlencode "text=$MSG" \
    --data-urlencode "parse_mode=Markdown" >/dev/null 2>&1
fi

echo "$CURRENT" > "$STATE"
