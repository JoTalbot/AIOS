#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}"
ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-/opt/android-sdk}"
AVD_NAME="${AIOS_AVD_NAME:-AIOS_Slando}"
EMULATOR_BIN="${ANDROID_SDK_ROOT}/emulator/emulator"

export PATH="${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools:${ANDROID_SDK_ROOT}/emulator:${PATH}"

echo "==> [bootstrap] Repo root: ${REPO_ROOT}"
echo "==> [bootstrap] Android SDK: ${ANDROID_SDK_ROOT}"
echo "==> [bootstrap] AVD: ${AVD_NAME}"

if ! command -v adb >/dev/null 2>&1; then
  echo "==> adb not found in PATH, expected under ${ANDROID_SDK_ROOT}/platform-tools"
  exit 1
fi

if ! "${EMULATOR_BIN}" -list-avds >/dev/null 2>&1; then
  echo "==> Emulator binary not usable"
  exit 1
fi

if ! "${EMULATOR_BIN}" -list-avds | grep -q "^${AVD_NAME}$"; then
  echo "==> AVD '${AVD_NAME}' not found, run setup/android-emulator-env.sh first"
  exit 1
fi

echo "==> [bootstrap] Installing Python dependencies"
python3 -m pip install --upgrade pip
python3 -m pip install pytest pytest-asyncio httpx graphql-core websockets grpcio

echo "==> [bootstrap] Starting emulator '${AVD_NAME}'"
bash "${SCRIPT_DIR}/android-emulator-run.sh" &
BOOT_PID=$!

echo "==> [bootstrap] Waiting for emulator device"
for i in $(seq 1 120); do
  if adb devices | grep -q 'emulator-5554.*device'; then
    echo "==> [bootstrap] Emulator ready"
    break
  fi
  sleep 2
done

adb wait-for-device
boot=$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)
if [ "$boot" != "1" ]; then
  echo "==> [bootstrap] Waiting for Android boot"
  for i in $(seq 1 180); do
    boot=$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)
    if [ "$boot" = "1" ]; then
      break
    fi
    sleep 2
  done
fi

echo "==> [bootstrap] Verifying tests"
python3 -m pytest tests/test_android_rpa_bridge.py -q

echo "==> [bootstrap] Run real emulator test"
python3 "${REPO_ROOT}/test_real_android_app.py" --package ua.slando --device emulator-5554

echo "==> [bootstrap] Done"
