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
install -d -m 0755 /var/lib/aios-alert-canary /var/lib/aios-telegram-metrics \
    /var/lib/aios/releases
install -d -m 0700 /var/lib/aios/telegram /var/log/aios/telegram \
    /var/backups/aios/telegram-queues \
    /var/backups/aios/telegram-queue-keys
if ! getent passwd aios-telegram >/dev/null; then
    useradd --system --home-dir /nonexistent --shell /usr/sbin/nologin \
        --user-group aios-telegram
fi
# Permit traversal to the root-owned read-only code checkout without granting
# access to /root itself or to the root-only .env file.
setfacl -m u:aios-telegram:--x /root
chown -R aios-telegram:aios-telegram /var/lib/aios/telegram /var/log/aios/telegram
if [ ! -e /etc/aios/colab-mode ]; then
    printf 'human_action_required\n' > /etc/aios/colab-mode
    chmod 0644 /etc/aios/colab-mode
fi
chown 65534:65534 /var/lib/aios-alert-canary
chmod 0750 /var/lib/aios-alert-canary
"${AIOS_PYTHON:-/opt/aios/.venv/bin/python}" \
    "$ROOT/scripts/prepare_docker_runtime_credentials.py"
# Historic secret archives are retained for recovery but never left world-readable.
find "$ROOT/backups" -type f -name '*secrets-config*' -exec chmod 0600 {} + 2>/dev/null || true

# Production historically uses aios-telegram-bot.service while fresh installs
# use aios-tg.service. Preserve the active base unit and add credentials via a
# drop-in instead of creating a second polling process.
if systemctl cat aios-telegram-bot.service >/dev/null 2>&1; then
    install -d -m 0755 "$UNIT_DST/aios-telegram-bot.service.d"
    cat > "$UNIT_DST/aios-telegram-bot.service.d/30-systemd-credentials.conf" <<EOF
[Service]
User=aios-telegram
Group=aios-telegram
LoadCredential=telegram_token:$CRED_DIR/telegram_token
LoadCredential=telegram_queue_key:$CRED_DIR/telegram_queue_key
LoadCredential=telegram_owner_chat_id:$CRED_DIR/telegram_owner_chat_id
Environment=AIOS_TELEGRAM_STATE_DIR=/var/lib/aios/telegram
Environment=AIOS_TELEGRAM_LOG_DIR=/var/log/aios/telegram
Environment=AIOS_TELEGRAM_BACKUP_DIR=/var/backups/aios/telegram-queues
Environment=HOME=/var/lib/aios/telegram
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=TELEGRAM_PROMETHEUS_ENABLED=0
Environment=TELEGRAM_DRAIN_TIMEOUT=45
StandardOutput=append:/var/log/aios/telegram/tg.log
StandardError=append:/var/log/aios/telegram/tg.log
TimeoutStopSec=110
KillSignal=SIGTERM
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
RestrictSUIDSGID=true
LockPersonality=true
CapabilityBoundingSet=
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
ProtectProc=invisible
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
    aios-docker-runtime-credentials.service \
    aios-telegram-metrics-snapshot.service \
    aios-telegram-queue-backup.service \
    aios-telegram-queue-backup.timer \
    aios-telegram-queue-restore-drill.service \
    aios-telegram-queue-restore-drill.timer \
    aios-telegram-offsite-backup.service \
    aios-telegram-offsite-backup.timer \
    aios-alertmanager-delivery-canary.service \
    aios-alertmanager-delivery-canary.timer; do
    install -m 0644 "$UNIT_SRC/$unit" "$UNIT_DST/"
done

systemctl daemon-reload
systemctl enable --now aios-docker-runtime-credentials.service
# The credential-backed aios-colab-keeper replaces the historical LLM runner.
# Keep automatic Colab recovery and the unused Whisper transcriber disabled
# until the owner explicitly resumes the managed keeper after any CAPTCHA.
for legacy_unit in aios-colab-llm.service aios-colab-whisper-keeper.service; do
    if systemctl cat "$legacy_unit" >/dev/null 2>&1; then
        systemctl disable --now "$legacy_unit" || true
    fi
done
systemctl enable --now aios-telegram-metrics-snapshot.service
systemctl enable --now aios-telegram-colab-canary.timer
systemctl enable --now aios-telegram-metrics-report.timer
systemctl enable --now aios-telegram-queue-backup.timer
systemctl enable --now aios-telegram-queue-restore-drill.timer
systemctl enable --now aios-telegram-offsite-backup.timer
systemctl enable --now aios-alertmanager-delivery-canary.timer
"${AIOS_PYTHON:-/opt/aios/.venv/bin/python}" \
    "$ROOT/scripts/generate_release_manifest.py"

echo "telegram_resilience_timers=enabled"
