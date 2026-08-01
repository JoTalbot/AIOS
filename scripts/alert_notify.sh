#!/bin/bash
# AIOS alert notifier: polls Prometheus for firing alerts and sends to Telegram.
# Run every minute via cron. Avoids duplicate sends by tracking last fired set.
set -uo pipefail

PROM="http://127.0.0.1:9090"
TOKEN="8374235817:AAFYRj2DJGcBLfJU7MeHX6CFwbP1AkwsDok"
CHAT="588113957"
STATE="/root/AIOS/data/metrics_exporter/.alerts_state"
mkdir -p "$(dirname "$STATE")"

# Get firing alert "name|labels" set
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

# Newly firing = in CURRENT but not PREV
NEW=$(comm -23 <(printf '%s\n' "$CURRENT") <(printf '%s\n' "$PREV") | grep -v "^$")

if [ -n "$NEW" ]; then
  MSG="⚠️ *AIOS Alert*%0A"
  while IFS= read -r a; do
    [ -z "$a" ] && continue
    MSG="${MSG}• $a%0A"
  done <<< "$NEW"
  curl -s -m 10 "https://api.telegram.org/bot$TOKEN/sendMessage" \
    --data-urlencode "chat_id=$CHAT" \
    --data-urlencode "text=$(echo -e "$MSG" | sed "s/%0A/\n/g")" \
    --data-urlencode "parse_mode=Markdown" >/dev/null 2>&1
fi

echo "$CURRENT" > "$STATE"
