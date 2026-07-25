#!/bin/bash
# AIOS production install script (Ubuntu 24.04+)
# Usage: bash deploy/scripts/install.sh
set -e
cd "$(dirname "$0")/../.."
PROJ=$(pwd)
echo "=== Installing AIOS to $PROJ ==="

echo "--- apt deps ---"
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv git curl adb || true

echo "--- pip deps ---"
pip3 install --break-system-packages -r requirements.txt httpx

echo "--- dirs ---"
mkdir -p "$PROJ/logs" "$PROJ/data" /var/lib/aios/admin-data

echo "--- .env ---"
if [ ! -f "$PROJ/.env" ]; then
    if [ -f "$PROJ/.env.example" ]; then
        cp "$PROJ/.env.example" "$PROJ/.env"
    else
        cat > "$PROJ/.env" << EOF
AIOS_API_KEYS={"$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")":{"subject":"local-operator","roles":["admin"]}}
GRAFANA_PASSWORD=changeme
AIOS_TELEGRAM_TOKEN=
AIOS_ADMIN_DATA_DIR=/var/lib/aios/admin-data
AIOS_OLX_HTTP_DB=$PROJ/data/olx_http.sqlite
EOF
    fi
    echo "Created $PROJ/.env — EDIT IT before starting services!"
fi

echo "--- systemd units ---"
for svc in aios-api aios-mcp aios-dash aios-tg aios-olx-collector; do
    cp "$PROJ/deploy/systemd/$svc.service" /etc/systemd/system/
done
systemctl daemon-reload

echo "--- enable & start ---"
systemctl enable aios-api aios-mcp aios-dash aios-tg aios-olx-collector
systemctl restart aios-api aios-mcp aios-dash aios-tg aios-olx-collector || true

echo ""
echo "=== Done! ==="
echo "Dashboard:  http://$(hostname -I | awk '{print $1}'):8580/"
echo "API:        http://$(hostname -I | awk '{print $1}'):8500/health"
