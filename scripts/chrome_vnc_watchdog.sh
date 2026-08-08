#!/bin/bash
# AIOS Chrome VNC watchdog — probe CDP :9222, restart on failure, TG on state transitions.
# cron: */5 * * * *
LOG=/root/AIOS/logs/chrome_watchdog.log
STATE=/root/AIOS/logs/.chrome_watchdog_state
SERVICE=aios-chrome-vnc

probe() { curl -s -m 6 http://127.0.0.1:9222/json/version >/dev/null 2>&1; }

notify() {
  cd /root/AIOS && /opt/aios/.venv/bin/python -c "
from run_freelance_funnel import send_tg
send_tg('''$1''')
" >/dev/null 2>&1
}

now() { date '+%Y-%m-%d %H:%M:%S'; }
prev=$(cat "$STATE" 2>/dev/null || echo up)

if probe; then
  if [ "$prev" = "down" ]; then
    echo "$(now) RECOVERED: CDP back online" >> "$LOG"
    notify "✅ <b>Chrome VNC восстановлен</b> — CDP :9222 снова онлайн"
    echo up > "$STATE"
  fi
  exit 0
fi

sleep 5
if probe; then
  exit 0  # флап — пропускаем
fi

echo "$(now) CDP DOWN — restarting $SERVICE" >> "$LOG"
systemctl restart "$SERVICE"
sleep 15

if probe; then
  echo "$(now) restart OK" >> "$LOG"
  [ "$prev" != "down" ] && notify "🔄 <b>Chrome VNC перезапущен</b> — CDP :9222 был недоступен (повлияло бы на OLX/сообщения), restart помог ✅"
  echo up > "$STATE"
else
  echo "$(now) restart FAILED — still down" >> "$LOG"
  [ "$prev" != "down" ] && notify "🔴 <b>Chrome VNC НЕ ПОДНЯЛСЯ</b> — CDP :9222 мёртв даже после restart. Проверь VNC (:1) и профиль chrome_twin"
  echo down > "$STATE"
fi
