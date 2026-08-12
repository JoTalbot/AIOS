#!/usr/bin/env bash
set -euo pipefail

ROOT="${AIOS_ROOT:-/root/AIOS}"
UNIT_SRC="$ROOT/deploy/systemd"
UNIT_DST="/etc/systemd/system"
CRED_DIR="${AIOS_CREDENTIAL_SOURCE_DIR:-/etc/aios/credentials}"

"${AIOS_PYTHON:-/opt/aios/.venv/bin/python}" "$ROOT/scripts/install_systemd_credentials.py"

# Production historically uses aios-telegram-bot.service while fresh installs
# use aios-tg.service. Preserve the active base unit and add credentials via a
# drop-in instead of creating a second polling process.
if systemctl cat aios-telegram-bot.service >/dev/null 2>&1; then
    install -d -m 0755 "$UNIT_DST/aios-telegram-bot.service.d"
    cat > "$UNIT_DST/aios-telegram-bot.service.d/30-systemd-credentials.conf" <<EOF
[Service]
LoadCredential=telegram_token:$CRED_DIR/telegram_token
LoadCredential=telegram_queue_key:$CRED_DIR/telegram_queue_key
Environment=TELEGRAM_QUEUE_KEY_FILE=%d/telegram_queue_key
UMask=0077
EOF
else
    install -m 0644 "$UNIT_SRC/aios-tg.service" "$UNIT_DST/"
fi

# Preserve host-specific Chrome/CDP drop-ins on existing Colab keepers.
if systemctl cat aios-colab-keeper.service >/dev/null 2>&1; then
    install -d -m 0755 "$UNIT_DST/aios-colab-keeper.service.d"
    cat > "$UNIT_DST/aios-colab-keeper.service.d/30-systemd-credentials.conf" <<EOF
[Service]
LoadCredential=colab_llm_api_key:$CRED_DIR/colab_llm_api_key
LoadCredential=tailscale_auth_key:$CRED_DIR/tailscale_auth_key
Environment=AIOS_SYSTEMD_CREDENTIALS=1
Environment=AIOS_CREDENTIAL_SOURCE_DIR=$CRED_DIR
Environment=COLAB_TUNNEL_PROVIDER=auto
UMask=0077
EOF
else
    install -m 0644 "$UNIT_SRC/aios-colab-keeper.service" "$UNIT_DST/"
fi

install -m 0644 "$UNIT_SRC/aios-telegram-colab-canary.service" "$UNIT_DST/"
install -m 0644 "$UNIT_SRC/aios-telegram-colab-canary.timer" "$UNIT_DST/"
install -m 0644 "$UNIT_SRC/aios-telegram-metrics-report.service" "$UNIT_DST/"
install -m 0644 "$UNIT_SRC/aios-telegram-metrics-report.timer" "$UNIT_DST/"

systemctl daemon-reload
systemctl enable --now aios-telegram-colab-canary.timer
systemctl enable --now aios-telegram-metrics-report.timer

echo "telegram_resilience_timers=enabled"
