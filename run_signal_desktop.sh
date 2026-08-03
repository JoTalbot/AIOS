#!/usr/bin/env bash
# Persistent Signal Desktop launcher/watchdog for the AIOS VNC display.
set -Eeuo pipefail

export DISPLAY="${SIGNAL_DISPLAY:-:1}"
export XAUTHORITY="${XAUTHORITY:-/root/.Xauthority}"
# Electron/Chromium refuses root without this explicit override.
export ELECTRON_DISABLE_SANDBOX="${ELECTRON_DISABLE_SANDBOX:-1}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"

until xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; do
  sleep 3
done

while true; do
  # Electron children also include "signal-desktop" in argv. Only the main
  # process begins directly with --no-sandbox; helper/zygote processes must not
  # trick the watchdog into thinking the desktop client is healthy.
  if ! pgrep -f '^(/usr/bin|/opt/Signal)/signal-desktop --no-sandbox' >/dev/null 2>&1; then
    /usr/bin/signal-desktop --no-sandbox --disable-gpu --disable-gpu-compositing \
      --use-gl=swiftshader --disable-dev-shm-usage >> /root/AIOS/logs/signal_desktop.log 2>&1 || true
    sleep 5
  fi
  sleep 10
done
