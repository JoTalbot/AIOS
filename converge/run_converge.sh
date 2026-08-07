#!/bin/bash
set -euo pipefail
export AIOS_ROOT=/root/AIOS
export CONVERGE_HOST=127.0.0.1
export CONVERGE_PORT=8092
cd /root/AIOS/converge
exec /opt/aios/.venv/bin/python -m uvicorn app:app --host "$CONVERGE_HOST" --port "$CONVERGE_PORT" --root-path /converge
