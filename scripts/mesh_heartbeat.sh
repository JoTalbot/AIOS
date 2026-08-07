#!/usr/bin/env bash
# AIOS Mesh heartbeat: реальный battery heartbeat телефона в mesh fleet
set -u
SERIAL="10.203.95.7:5555"
BAT=$(/usr/local/bin/aios-adb -s "$SERIAL" shell dumpsys battery 2>/dev/null | grep -m1 'level:' | awk '{print $2}')
[ -z "$BAT" ] && BAT=0
/opt/aios/.venv/bin/python /root/AIOS/run_android_mesh.py --heartbeat "$SERIAL" --battery "$BAT" >/dev/null 2>&1 || true
