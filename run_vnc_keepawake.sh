#!/usr/bin/env bash
# Keep the automation VNC display awake for OCR-driven desktop adapters.
set -Eeuo pipefail

export DISPLAY="${AIOS_VNC_DISPLAY:-:1}"
export XAUTHORITY="${XAUTHORITY:-/root/.Xauthority}"

until xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; do
  sleep 3
done

while true; do
  # Xvnc may not expose DPMS; every command is intentionally best-effort.
  xset s off >/dev/null 2>&1 || true
  xset s reset >/dev/null 2>&1 || true
  xset -dpms >/dev/null 2>&1 || true
  xdg-screensaver reset >/dev/null 2>&1 || true
  xfce4-screensaver-command --deactivate >/dev/null 2>&1 || true
  sleep 60
done
