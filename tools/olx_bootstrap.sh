#!/usr/bin/env bash
# AIOS OLX Parser Agent — fresh server bootstrap wrapper.
# Prints the full setup plan by default; pass --execute to run it.
#
#   ./tools/olx_bootstrap.sh                 # print plan
#   ./tools/olx_bootstrap.sh --execute       # run end-to-end
#   ./tools/olx_bootstrap.sh --no-emulator   # physical device instead of AVD
#   ./tools/olx_bootstrap.sh --apk olx.apk   # install OLX APK as well
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

python3 "${PROJECT_ROOT}/aios_cli.py" olx bootstrap "$@"
