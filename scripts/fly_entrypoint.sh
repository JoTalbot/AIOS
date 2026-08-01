#!/bin/bash
echo "🌌 Запуск AIOS REST API (dashboard + full API)..."

# 1. Запускаем полный REST API (все роуты: stats, services, devices, ...) на 8000
#    auth_required=False + api_keys={}: внутри закрытой docker-сети (dashboard/mcp/autopilot)
echo "🚀 Поднятие REST API на 0.0.0.0:8000..."
PYTHONPATH=/app python3 -c "
import sys, os
sys.path.insert(0, '/app')
from aios_core.api.app import create_app
import uvicorn
app = create_app(
    db_path=os.environ.get('AIOS_MAIN_DB', '/app/data/aios.sqlite'),
    constitution_dir='/app/docs/constitution',
    policies_dir='/app/policies',
    auth_required=False,
    api_keys={},
)
uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')
" &

# 2. Запускаем P2P-ноду на отдельном порту 8001 (чтобы не терять p2p-функциональность)
echo "🚀 P2P-узел на 0.0.0.0:8001..."
PYTHONPATH=/app uvicorn aios_core.p2p_network:app --host 0.0.0.0 --port 8001 &

# 3. Бесконечный автономный цикл "AI CEO"
echo "💼 Инициализация фонового коммерческого контура..."
while true; do
    echo "[$(date)] Запуск коммерческого сканирования (Lead Generation)..."
    python3 /app/scripts/run_commercial_pipeline.py
    echo "💤 Цикл завершен. Ожидание 1 час перед следующим сканированием..."
    sleep 3600
done
