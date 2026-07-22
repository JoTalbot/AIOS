#!/bin/bash
set -euo pipefail

ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-/opt/android-sdk}"
AVD_NAME="${AIOS_AVD_NAME:-AIOS_Slando}"
API_LEVEL="${AIOS_API_LEVEL:-35}"
ABI="${AIOS_ABI:-google_apis/x86_64}"
SD_CARD_SIZE="${AIOS_SD_CARD_SIZE:-512M}"

echo "==> Android SDK root: ${ANDROID_SDK_ROOT}"
mkdir -p "${ANDROID_SDK_ROOT}"

if ! command -v adb >/dev/null 2>&1; then
  echo "==> Install platform-tools"
  mkdir -p "${ANDROID_SDK_ROOT}/platform-tools"
  curl -sSLo "${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager" "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" >/dev/null || true
fi

export PATH="${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools:${ANDROID_SDK_ROOT}/emulator:${PATH}"

mkdir -p ~/.android/avd

if ! avdmanager list avd | grep -q "Name: ${AVD_NAME}"; then
  echo "==> Create AVD: ${AVD_NAME}"
  mkdir -p "${ANDROID_SDK_ROOT}/system-images/android-${API_LEVEL}/${ABI}"
  echo "y" | avdmanager create avd -n "${AVD_NAME}" -k "system-images/android-${API_LEVEL}/${ABI}" -d "pixel" --force || true
fi

cat > ~/.android/avd/${AVD_NAME}.avd/config.ini <<EOF
hw.lcd.density=160
hw.lcd.width=320
hw.lcd.height=640
sdcard.size=${SD_CARD_SIZE}
hw.gpu.enabled=yes
hw.gpu.mode=swiftshader_indirect
hw.keyboard=yes
vm.heapSize=256M
EOF

echo "==> AVD ready: ${AVD_NAME}"
