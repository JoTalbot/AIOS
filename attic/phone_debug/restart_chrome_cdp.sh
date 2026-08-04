#!/bin/bash
# Останавливает мануальный Chrome и запускает systemd-сервис aios-chrome-vnc (с CDP 9222)
set +e
# 1. Остановить все chrome с этим профилем
pkill -9 -f "user-data-dir=/root/AIOS/data/chrome_twin/default" 2>/dev/null
sleep 4
# 2. Остановить systemd-сервис (на случай active)
systemctl stop aios-chrome-vnc.service 2>/dev/null
sleep 2
# 3. Запустить systemd-сервис
systemctl start aios-chrome-vnc.service
sleep 6
echo "=== сервис ==="
systemctl is-active aios-chrome-vnc.service
echo "=== CDP ==="
curl -s http://127.0.0.1:9222/json/version | head -c 60
echo
echo "=== chrome процессов ==="
pgrep -f user-data-dir= | wc -l
