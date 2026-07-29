#!/usr/bin/env bash
# AIOS CI — Android emulator bring-up (validated on GitHub-hosted runners).
#
# Usage: ci-android-emulator.sh [AVD_COUNT]
#   Boots AVD_COUNT emulators (default 1) named AIOS_1..N on ports 5554+.
#   After completion the serials are emulator-5554, emulator-5556, ...
#
# Every step encodes a lesson learned from a real CI failure:
#  - KVM udev rule           (x86_64 refuses to boot without hw acceleration)
#  - ANDROID_HOME pinned     (sdkmanager/avdmanager/emulator disagree otherwise)
#  - pipefail off for licenses (yes dies with SIGPIPE once sdkmanager exits)
#  - system image id uses ";" (slash form: "Failed to find package")
#  - config.ini APPEND only  (overwrite wipes abi.type -> "arm not supported")
set -euo pipefail

AVD_COUNT="${1:-1}"
: "${ANDROID_SDK_ROOT:=/opt/android-sdk}"
: "${API_LEVEL:=35}"
: "${ABI:=google_apis;x86_64}"

# Pin ANDROID_HOME to our SDK root for the SCRIPT ITSELF, not only for later
# workflow steps: GitHub-hosted runners preset ANDROID_HOME=/usr/local/lib/android/sdk
# and the emulator inherits it from this script's environment, then dies with
# "Broken AVD system path" because the system image lives under ANDROID_SDK_ROOT.
# (Dispatch run 30478262476: All three calibrate legs boot-timed-out on this.)
export ANDROID_HOME="${ANDROID_SDK_ROOT}"

echo "==> Bring up ${AVD_COUNT} emulator(s): SDK=${ANDROID_SDK_ROOT} API=${API_LEVEL} ABI=${ABI}"

# 1. KVM (required for x86_64 emulation on hosted runners)
echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666"' | sudo tee /etc/udev/rules.d/99-kvm4all.rules > /dev/null
sudo udevadm control --reload-rules
sudo udevadm trigger --name-match=kvm || true
ls -la /dev/kvm

# 2. System dependencies
sudo apt-get update -qq
sudo apt-get install -qq -y openjdk-17-jdk-headless unzip wget curl lz4 libpulse-dev libx11-6 libxext6 libxi6 libxrender1 libxtst6 libglib2.0-0

# 3. cmdline-tools
mkdir -p "${ANDROID_SDK_ROOT}/cmdline-tools"
cd "${ANDROID_SDK_ROOT}/cmdline-tools"
if [ ! -d latest ]; then
  wget -q "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" -O cmdline-tools.zip
  unzip -q cmdline-tools.zip
  mv cmdline-tools latest
  rm cmdline-tools.zip
fi
export PATH="${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools:${ANDROID_SDK_ROOT}/emulator:${PATH}"

# Share with subsequent workflow steps (no-op outside GitHub Actions)
echo "ANDROID_HOME=${ANDROID_SDK_ROOT}" >> "${GITHUB_ENV:-/dev/null}" 2>/dev/null || true
echo "ANDROID_SDK_ROOT=${ANDROID_SDK_ROOT}" >> "${GITHUB_ENV:-/dev/null}" 2>/dev/null || true
echo "${ANDROID_SDK_ROOT}/platform-tools" >> "${GITHUB_PATH:-/dev/null}" 2>/dev/null || true

# 4. Licenses (pipefail off: 'yes' dies with SIGPIPE once sdkmanager exits)
set +o pipefail
yes | sdkmanager --licenses > /dev/null
set -o pipefail

# 5. Packages
sdkmanager "platform-tools" "emulator" "platforms;android-${API_LEVEL}" \
  "system-images;android-${API_LEVEL};${ABI}" "build-tools;35.0.0" > /dev/null
sdkmanager --list_installed | grep -Ei "system-images|platform-tools|emulator" || true

# 6. AVDs (pin AVD storage so avdmanager and the config writer agree)
export ANDROID_SDK_HOME="$HOME"
export ANDROID_AVD_HOME="$HOME/.android/avd"
mkdir -p "$ANDROID_AVD_HOME"
for i in $(seq 1 "$AVD_COUNT"); do
  AVD="AIOS_${i}"
  echo "no" | avdmanager create avd -n "${AVD}" \
    -k "system-images;android-${API_LEVEL};${ABI}" -d "pixel" --force > /dev/null
  # APPEND (>>) — never overwrite: config.ini holds abi.type/image.sysdir
  cat >> "${ANDROID_AVD_HOME}/${AVD}.avd/config.ini" <<EOF
hw.lcd.density=160
hw.lcd.width=320
hw.lcd.height=640
sdcard.size=512M
hw.gpu.enabled=yes
hw.gpu.mode=swiftshader_indirect
hw.keyboard=yes
vm.heapSize=256M
hw.ramSize=1536
EOF
done

# 7. Boot
for i in $(seq 1 "$AVD_COUNT"); do
  PORT=$((5554 + (i - 1) * 2))
  emulator -avd "AIOS_${i}" -no-snapshot-load -no-audio -no-boot-anim \
    -gpu swiftshader_indirect -no-window -no-metrics -port "${PORT}" \
    > "/tmp/emulator_${i}.log" 2>&1 &
  echo "Started AIOS_${i} on port ${PORT}"
done

# 8. Wait for boot
for i in $(seq 1 "$AVD_COUNT"); do
  PORT=$((5554 + (i - 1) * 2))
  SERIAL="emulator-${PORT}"
  echo "Waiting for ${SERIAL}..."
  timeout 420 bash -c "
    until adb -s ${SERIAL} shell getprop sys.boot_completed 2>/dev/null | grep -q '1'; do
      sleep 5
    done
  " || { echo "Timeout waiting for ${SERIAL}"; cat "/tmp/emulator_${i}.log"; exit 1; }
  echo "${SERIAL} booted"
done
adb devices
echo "==> Emulator(s) ready"
