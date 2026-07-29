#!/usr/bin/env bash
# AIOS — Android SDK + AVD provisioning for servers (VPS) and local Linux.
# Idempotent: safe to re-run; only missing pieces are installed.
# Used by the full-ci-cd deploy job on the VPS and by scripts/android/QUICKSTART.md.
#
# Environment overrides:
#   ANDROID_SDK_ROOT   SDK location            (default /opt/android-sdk)
#   AIOS_AVD_NAME      AVD name                (default AIOS_Slando)
#   AIOS_API_LEVEL     Android API level       (default 35)
#   AIOS_ABI           system image ABI        (default google_apis;x86_64;
#                                              slash form google_apis/x86_64 is accepted and normalized)
#   AIOS_SD_CARD_SIZE  sdcard.size for the AVD (default 512M)
#
# Every step encodes a lesson learned from a real CI/deploy failure:
#  - system-image package id uses ";" segments      (slash form -> "Failed to find package")
#  - NEVER overwrite config.ini, append only        (overwrite wipes abi.type -> "arm not supported by QEMU2")
#  - the system image must be INSTALLED by sdkmanager (mkdir of its directory provisions an empty folder)
#  - licenses: 'yes | sdkmanager --licenses' dies with SIGPIPE under pipefail -> toggle pipefail off
#  - cmdline-tools must be unpacked as cmdline-tools/latest (old script curled the ZIP over the sdkmanager binary)
#  - x86_64 emulation needs /dev/kvm (udev rule when the device exists but is not writable)
set -euo pipefail

ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-/opt/android-sdk}"
AVD_NAME="${AIOS_AVD_NAME:-AIOS_Slando}"
API_LEVEL="${AIOS_API_LEVEL:-35}"
ABI="${AIOS_ABI:-google_apis;x86_64}"
SD_CARD_SIZE="${AIOS_SD_CARD_SIZE:-512M}"
# Normalize slash form (google_apis/x86_64) to sdkmanager package-id form (google_apis;x86_64)
ABI="${ABI//\//;}"

# Pin ANDROID_HOME to our SDK root: runner/CI images often preset ANDROID_HOME
# to another SDK, and avdmanager/emulator then look for system images in the
# wrong tree ("Broken AVD system path").
export ANDROID_HOME="${ANDROID_SDK_ROOT}"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  SUDO="$(command -v sudo || true)"
fi

echo "==> Android SDK root: ${ANDROID_SDK_ROOT} | AVD: ${AVD_NAME} | API: ${API_LEVEL} | ABI: ${ABI}"
mkdir -p "${ANDROID_SDK_ROOT}"

# 1. KVM: x86_64 emulation requires hardware acceleration.
if [ -e /dev/kvm ] && [ ! -w /dev/kvm ]; then
  echo "==> /dev/kvm exists but is not writable — installing udev rule"
  echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666"' | ${SUDO} tee /etc/udev/rules.d/99-kvm4all.rules > /dev/null || true
  ${SUDO} udevadm control --reload-rules 2>/dev/null || true
  ${SUDO} udevadm trigger --name-match=kvm 2>/dev/null || true
fi
if [ ! -e /dev/kvm ]; then
  echo "!! WARNING: /dev/kvm is missing — x86_64 guests need KVM; the AVD will NOT boot on this host."
fi

# 2. Base tools (best effort; sdkmanager needs java, provisioning needs unzip/wget)
if ! command -v java >/dev/null 2>&1 || ! command -v unzip >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    echo "==> Installing openjdk-17 / unzip / wget / curl"
    ${SUDO} apt-get update -qq || true
    ${SUDO} apt-get install -qq -y openjdk-17-jdk-headless unzip wget curl || true
  fi
fi

# 3. cmdline-tools (sdkmanager lives here). Old script downloaded the ZIP straight
#    onto the sdkmanager binary path — that file must be an unpacked directory.
mkdir -p "${ANDROID_SDK_ROOT}/cmdline-tools"
if [ ! -x "${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager" ]; then
  echo "==> Installing Android cmdline-tools"
  TMP_DIR="$(mktemp -d)"
  wget -q "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" -O "${TMP_DIR}/tools.zip"
  unzip -q "${TMP_DIR}/tools.zip" -d "${TMP_DIR}"
  rm -rf "${ANDROID_SDK_ROOT}/cmdline-tools/latest"
  mv "${TMP_DIR}/cmdline-tools" "${ANDROID_SDK_ROOT}/cmdline-tools/latest"
  rm -rf "${TMP_DIR}"
fi
export PATH="${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools:${ANDROID_SDK_ROOT}/emulator:${PATH}"

# 4. Licenses. pipefail OFF: 'yes' is killed by SIGPIPE once sdkmanager stops
#    reading, which would otherwise abort the script with exit code 141.
set +o pipefail
yes | sdkmanager --licenses > /dev/null
set -o pipefail

# 5. Packages — platform-tools (adb), emulator, platform AND the system image itself.
echo "==> sdkmanager install: platform-tools, emulator, platforms;android-${API_LEVEL}, system-images;android-${API_LEVEL};${ABI}"
sdkmanager "platform-tools" "emulator" "platforms;android-${API_LEVEL}" \
  "system-images;android-${API_LEVEL};${ABI}" > /dev/null

# 6. AVD (pin storage so avdmanager and the config writer agree on the location).
export ANDROID_SDK_HOME="${ANDROID_SDK_HOME:-$HOME}"
export ANDROID_AVD_HOME="${ANDROID_AVD_HOME:-$HOME/.android/avd}"
mkdir -p "${ANDROID_AVD_HOME}"
if ! avdmanager list avd | grep -q "Name: ${AVD_NAME}"; then
  echo "==> Create AVD: ${AVD_NAME}"
  echo "no" | avdmanager create avd -n "${AVD_NAME}" \
    -k "system-images;android-${API_LEVEL};${ABI}" -d "pixel" --force > /dev/null
fi

# 7. Hardware profile — APPEND (>>) only. Overwriting config.ini wipes abi.type /
#    image.sysdir entries, then QEMU reports an unsupported CPU architecture.
if [ -f "${ANDROID_AVD_HOME}/${AVD_NAME}.avd/config.ini" ]; then
  cat >> "${ANDROID_AVD_HOME}/${AVD_NAME}.avd/config.ini" <<EOF
hw.lcd.density=160
hw.lcd.width=320
hw.lcd.height=640
sdcard.size=${SD_CARD_SIZE}
hw.gpu.enabled=yes
hw.gpu.mode=swiftshader_indirect
hw.keyboard=yes
vm.heapSize=256M
hw.ramSize=1536
EOF
fi

echo "==> AVD ready: ${AVD_NAME}"
echo "==> Boot: ${ANDROID_SDK_ROOT}/emulator/emulator -avd ${AVD_NAME} -no-snapshot-load -no-audio -no-boot-anim -gpu swiftshader_indirect -no-window -no-metrics"
