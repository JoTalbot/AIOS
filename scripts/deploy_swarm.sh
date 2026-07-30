#!/bin/bash
echo "🚀 Инициализация боевого роя AIOS (Docker Swarm Mode)..."
docker swarm init 2>/dev/null || true
docker stack deploy -c docker-compose.unified.yml aios_production_swarm
echo "✅ Рой успешно развернут! Доступные порты: 3000 (UI), 8000 (API), 3001 (Grafana)"
