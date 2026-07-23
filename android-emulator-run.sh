#!/bin/bash
set -euo pipefail

ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-/opt/android-sdk}"
AVD_NAME="${AIOS_AVD_NAME:-AIOS_Slando}"
EMULATOR_BIN="${ANDROID_SDK_ROOT}/emulator/emulator"

if ! command -v adb >/dev/null 2>&1; then
  echo "ADB is not installed or not in PATH"
  exit 1
fi

if ! "${EMULATOR_BIN}" -list-avds >/dev/null 2>&1; then
  echo "Emulator binary not usable"
  exit 1
fi

if ! "${EMULATOR_BIN}" -list-avds | grep -q "^${AVD_NAME}$"; then
  echo "AVD '${AVD_NAME}' not found, run setup/android-emulator-env.sh first"
  exit 1
fi

echo "==> Launching emulator '${AVD_NAME}'"
"${EMULATOR_BIN}" \
  -avd "${AVD_NAME}" \
  -no-window \
  -no-audio \
  -gpu swiftshader_indirect \
  -netdelay none \
  -netspeed full
