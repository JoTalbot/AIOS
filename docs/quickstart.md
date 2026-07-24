# Быстрый старт

Полный гайд по установке и запуску AIOS за 30 минут.

## Системные требования

- Python 3.11+
- Docker & Docker Compose (для контейнерного запуска)
- 2 GB RAM, 4 GB диск
- (Опционально) Android SDK для работы с устройствами

## 1. Клонирование репозитория

```bash
git clone https://github.com/JoTalbot/AIOS.git
cd AIOS
```

## 2. Установка зависимостей

```bash
python -m pip install -r requirements.txt
```

Зависимости:
- `starlette`, `uvicorn` — HTTP/REST сервер
- `sqlite3` (встроен) — персистентность
- `httpx` — HTTP-клиент
- `pytest` — тестирование

## 3. Запуск тестов

```bash
python -m pytest -q
```

Последний воспроизводимый локальный аудит (2026-07-23, Python 3.13): **1255 passed**. Результат может отличаться в зависимости от платформы и выбранных маркеров.

## 4. Запуск REST API

```bash
# Настройте API-ключи (обязательно!). Не используйте этот пример как реальный ключ.
# В Docker: cp .env.example .env и замените все значения-заглушки.
export AIOS_API_KEYS='{
  "my-secret-key": {
    "subject": "developer",
    "roles": ["admin"]
  }
}'

# Запуск
python run_rest_api.py --host 127.0.0.1 --port 8000 --db ./aios.sqlite
```

API доступен на `http://127.0.0.1:8000`. Health check не требует аутентификации:

```bash
curl http://127.0.0.1:8000/health
```

Все остальные эндпоинты требуют Bearer-токен:

```bash
curl -H 'Authorization: Bearer my-secret-key' http://127.0.0.1:8000/api/v1/stats
```

## 5. MCP Server

```bash
export AIOS_API_KEYS='{"my-secret-key":{"subject":"developer","roles":["admin"]}}'
python run_mcp_server.py --host 127.0.0.1 --port 8471 --db ./aios.sqlite
```

MCP endpoint: JSON-RPC 2.0 для tools/resources/prompts.

## 6. Web Dashboard

```bash
python run_dashboard.py
# Откройте http://127.0.0.1:8080
```

## 7. Docker (рекомендуется для production)

### Development

```bash
docker-compose up -d --build
curl http://localhost:8000/health
```

### Production

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

Production-сте включает:
- **API** (2 CPU, 2 GB RAM limits)
- **Autopilot daemon** (interval 900s)
- **Dashboard** (port 8080)
- **Prometheus** (port 9090, 2 scrape configs)
- **Grafana** (port 3000, 2 dashboards: ops + production)

## 8. Production Autopilot

```bash
# Симуляция 2-недельного GA-прогона
python run_production_autopilot.py --simulate-2weeks --cycles-per-day 24 --verbose --output report.json

# Проверка здоровья
python run_production_autopilot.py --health

# Prometheus-метрики
python run_production_autopilot.py --prometheus-metrics

# Daemon mode (реальная эксплуатация)
python run_production_autopilot.py --daemon --interval 900 --verbose
```

## 9. Онбординг новой платформы (≤30 минут)

```bash
# Создание скелета платформы
aios platforms scaffold --platform prom --package com.prom.ua --type marketplace

# Калибровочный рецепт (ADB-команды)
aios platforms doctor --platform prom --calibrate-recipe

# На живом устройстве:
aios platforms calibrate --platform prom --dump /tmp/ui.xml --write
aios platforms codegen --platform prom --force
aios platforms bootup --verify
```

## 10. Использование SDK

```python
import asyncio
from aios_sdk import AIOSClient

async def main():
    async with AIOSClient("http://localhost:8000", api_key="my-secret-key") as client:
        health = await client.health()
        stats = await client.stats()
        print(f"AIOS: {health['status']}, tasks: {stats['tasks_total']}")

asyncio.run(main())
```

## Мониторинг

```bash
# CLI-мониторинг
python monitor.py --url http://localhost:8000 --interval 30

# Prometheus-метрики
curl http://localhost:8000/metrics

# Grafana (production)
open http://localhost:3000
```

## Далее

- [Полная документация по архитектуре](architecture.md)
- [Production Exploitation Guide](PRODUCTION.md)
- [API Reference](api.md)
- [Роадмап](ROADMAP_FULL.md)
