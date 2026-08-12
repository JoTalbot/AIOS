#!/usr/bin/env bash
set -euo pipefail

ROOT="${AIOS_ROOT:-/root/AIOS}"
UNIT_SRC="$ROOT/deploy/systemd"
UNIT_DST="/etc/systemd/system"
CRED_DIR="${AIOS_CREDENTIAL_SOURCE_DIR:-/etc/aios/credentials}"

CREDENTIAL_ARGS=()
if [ "${AIOS_PURGE_LEGACY_SECRETS:-1}" = "1" ]; then
    CREDENTIAL_ARGS+=(--purge-managed-env)
fi
"${AIOS_PYTHON:-/opt/aios/.venv/bin/python}" \
    "$ROOT/scripts/install_systemd_credentials.py" "${CREDENTIAL_ARGS[@]}"
"${AIOS_PYTHON:-/opt/aios/.venv/bin/python}" \
    "$ROOT/scripts/render_alertmanager_config.py"
install -d -m 0755 /var/lib/aios-alert-canary /var/lib/aios-telegram-metrics
install -d -m 0700 /root/AIOS/backups/telegram-queues \
    /root/aios-secret-backups/telegram-queue-keys
# Historic secret archives are retained for recovery but never left world-readable.
find "$ROOT/backups" -type f -name '*secrets-config*' -exec chmod 0600 {} + 2>/dev/null || true

# Production historically uses aios-telegram-bot.service while fresh installs
# use aios-tg.service. Preserve the active base unit and add credentials via a
# drop-in instead of creating a second polling process.
if systemctl cat aios-telegram-bot.service >/dev/null 2>&1; then
    install -d -m 0755 "$UNIT_DST/aios-telegram-bot.service.d"
    cat > "$UNIT_DST/aios-telegram-bot.service.d/30-systemd-credentials.conf" <<EOF
[Service]
LoadCredential=telegram_token:$CRED_DIR/telegram_token
LoadCredential=telegram_queue_key:$CRED_DIR/telegram_queue_key
LoadCredential=telegram_owner_chat_id:$CRED_DIR/telegram_owner_chat_id
Environment=TELEGRAM_QUEUE_KEY_FILE=%d/telegram_queue_key
Environment=TELEGRAM_PROMETHEUS_ENABLED=0
Environment=TELEGRAM_DRAIN_TIMEOUT=45
TimeoutStopSec=110
KillSignal=SIGTERM
UMask=0077
EOF
else
    install -m 0644 "$UNIT_SRC/aios-tg.service" "$UNIT_DST/"
fi

# Keep the secondary Colab browser below its cgroup limit and prevent a crash
# loop from restoring every historical tab at once.
CHROME_DROPIN="$ROOT/deploy/systemd/aios-chrome-colab-secondary.service.d/40-memory-safe-startup.conf"
if systemctl cat aios-chrome-colab-secondary.service >/dev/null 2>&1 && [ -f "$CHROME_DROPIN" ]; then
    install -d -m 0755 "$UNIT_DST/aios-chrome-colab-secondary.service.d"
    install -m 0644 "$CHROME_DROPIN" \
        "$UNIT_DST/aios-chrome-colab-secondary.service.d/40-memory-safe-startup.conf"
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
for unit in \
    aios-telegram-metrics-snapshot.service \
    aios-telegram-queue-backup.service \
    aios-telegram-queue-backup.timer \
    aios-telegram-queue-restore-drill.service \
    aios-telegram-queue-restore-drill.timer \
    aios-alertmanager-delivery-canary.service \
    aios-alertmanager-delivery-canary.timer; do
    install -m 0644 "$UNIT_SRC/$unit" "$UNIT_DST/"
done

systemctl daemon-reload
systemctl enable --now aios-telegram-metrics-snapshot.service
systemctl enable --now aios-telegram-colab-canary.timer
systemctl enable --now aios-telegram-metrics-report.timer
systemctl enable --now aios-telegram-queue-backup.timer
systemctl enable --now aios-telegram-queue-restore-drill.timer
systemctl enable --now aios-alertmanager-delivery-canary.timer

echo "telegram_resilience_timers=enabled"
