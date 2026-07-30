#!/usr/bin/env bash
set -euo pipefail
LOCK="/root/agents/-Octopus/skills/core/money-earner-orchestrator/data/locks/external_side_effects.lock"
mkdir -p "$(dirname "$LOCK")"
exec 9>"$LOCK"
flock -n 9 || { echo "external-effect lock busy" >&2; exit 75; }
export OCTOPUS_EXTERNAL_EFFECT_LOCKED=1
exec "$@"
