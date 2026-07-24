#!/bin/bash
set -e

# =========================================================
# AIOS: 1-Click Deployment Script
# =========================================================
# This script initializes the whole environment:
# 1. Start the core backend and dashboard
# 2. Build and run the Android Emulator container for Mobile RPA
# =========================================================

echo "🚀 Начинаем деплой AIOS..."

if [ ! -f ".env" ]; then
    echo "⚠️ .env файл не найден! Создаем из .env.example..."
    cp .env.example .env
fi

echo "📦 1. Запуск базовой инфраструктуры (API, MCP, Dashboard)..."
docker-compose up -d --build

echo "📱 2. Сборка и запуск контейнера с Android эмулятором (Мобильная RPA)..."
docker build -f Dockerfile.android -t aios-android-env .

echo "🔥 3. Запуск Android эмулятора в фоне..."
docker run -d --name aios-android-emulator \
  --privileged \
  -v /dev/kvm:/dev/kvm \
  -p 5554:5554 \
  -p 5555:5555 \
  aios-android-env

echo "✅ Деплой успешно запущен!"
echo "👉 Dashboard: http://localhost:8080"
echo "👉 REST API: http://localhost:8000"
echo ""
echo "📱 Для просмотра логов Android-эмулятора выполните:"
echo "   docker logs -f aios-android-emulator"
