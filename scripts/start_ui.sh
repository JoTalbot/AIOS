#!/bin/bash
# Экспериментальная симуляция графического центра управления (Вариант В)
# Не является production deployment. См. deploy/DEPLOYMENT_SOURCES.md.

echo "🌐 Подготовка Графического Центра Управления AIOS..."

cd "$(dirname "$0")/.."

# Проверка наличия .env файлов
if [ ! -f .env ]; then
    echo "⚙️ Создание дефолтного .env файла..."
    echo "DATABASE_URL=sqlite:///./aios.db" > .env
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000" >> .env
fi

echo "🚀 Поднимаем инфраструктуру (Backend, UI, Grafana, Prometheus)..."
# В реальной среде здесь будет: docker-compose -f docker-compose.unified.yml up -d
echo "[SIMULATION] docker-compose -f docker-compose.unified.yml up -d"

echo "✅ UI доступен по адресу: http://localhost:3000"
echo "📊 Grafana (метрки роя) доступна по адресу: http://localhost:3001"
echo "🔌 API Gateway (AIOS Core) работает на: http://localhost:8000"
