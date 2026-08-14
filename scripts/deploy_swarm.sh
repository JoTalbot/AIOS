#!/usr/bin/env bash
set -euo pipefail

# EXPERIMENTAL ONLY. This is not the canonical AIOS production deployment.
# See deploy/DEPLOYMENT_SOURCES.md.
if [[ "${AIOS_ALLOW_EXPERIMENTAL_SWARM:-0}" != "1" ]]; then
  echo "Отказ: experimental Swarm отключён по умолчанию." >&2
  echo "Для осознанного теста: AIOS_ALLOW_EXPERIMENTAL_SWARM=1 $0" >&2
  exit 2
fi

echo "🧪 Запуск экспериментального AIOS UI/Swarm stack..."
docker swarm init 2>/dev/null || true
docker stack deploy -c docker-compose.unified.yml aios_experimental_swarm
echo "✅ Экспериментальный stack запущен: UI 3000, API 8000, Grafana 3001"
