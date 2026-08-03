#!/usr/bin/env bash
# Persistent Viber Desktop launcher/watchdog for the AIOS VNC display.
set -Eeuo pipefail

export DISPLAY="${VIBER_DISPLAY:-:1}"
export XAUTHORITY="${XAUTHORITY:-/root/.Xauthority}"
export QT_X11_NO_MITSHM="${QT_X11_NO_MITSHM:-1}"
# Viber Desktop embeds Qt WebEngine/Chromium; root requires this override.
export QTWEBENGINE_DISABLE_SANDBOX="${QTWEBENGINE_DISABLE_SANDBOX:-1}"
: "${QTWEBENGINE_CHROMIUM_FLAGS:=--no-sandbox --disable-gpu}"
export QTWEBENGINE_CHROMIUM_FLAGS

# Native VNC may start later than systemd. Wait instead of starting Viber on a
# nonexistent display and losing the saved desktop session.
until xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; do
  sleep 3
done

# Viber daemonizes after launch on this build. Keep a foreground watchdog as
# systemd's main process so a closed/crashed desktop client is relaunched.
while true; do
  if ! pgrep -f '^/opt/viber/Viber([[:space:]]|$)' >/dev/null 2>&1; then
    /opt/viber/Viber >> /root/AIOS/logs/viber_desktop.log 2>&1 || true
    sleep 5
  fi
  sleep 10
done
