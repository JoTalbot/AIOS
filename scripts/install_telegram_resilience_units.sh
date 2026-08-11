#!/usr/bin/env bash
set -euo pipefail

ROOT="${AIOS_ROOT:-/root/AIOS}"
UNIT_SRC="$ROOT/deploy/systemd"
UNIT_DST="/etc/systemd/system"

install -m 0644 "$UNIT_SRC/aios-telegram-colab-canary.service" "$UNIT_DST/"
install -m 0644 "$UNIT_SRC/aios-telegram-colab-canary.timer" "$UNIT_DST/"
install -m 0644 "$UNIT_SRC/aios-telegram-metrics-report.service" "$UNIT_DST/"
install -m 0644 "$UNIT_SRC/aios-telegram-metrics-report.timer" "$UNIT_DST/"

systemctl daemon-reload
systemctl enable --now aios-telegram-colab-canary.timer
systemctl enable --now aios-telegram-metrics-report.timer

echo "telegram_resilience_timers=enabled"
