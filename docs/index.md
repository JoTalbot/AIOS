# AIOS — Autonomous Intelligence Operating System

**Версия:** 9.2.0-production | **Тесты:** 1010 passing | **Дата:** 23 июля 2026

AIOS — саморазвивающаяся распределённая операционная система для интеллекта приложений,
автоматизированного тестирования, генерации API, эволюции навыков и коллективного обучения.
Работает на **Octopus Runtime**.

---

## Компоненты

- **Конституция и политики** — загрузка правил и конвейер принятия решений в рантайме (67 статей)
- **Оркестратор** — последовательное выполнение задач с конституционной оценкой
- **SQLite-персистентность** — аудит, одобрения, память, граф знаний и записи эволюции
- **MCP Gateway** — JSON-RPC 2.0 интерфейс для инструментов, ресурсов и промптов
- **REST API** — Starlette-приложение, раскрывающее подсистемы рантайма (143 маршрута)
- **Production Autopilot** — промышленная эксплуатация с compliance, pacing и predictive risk
- **AI Advisor** — интеллектуальный советник с draft-only режимом и human-approve
- **SDK v4.2.0** — официальный Python-клиент (async + sync)
- **Marketplace v2** — публикация и обнаружение плагинов платформ

## Быстрый старт

```bash
# Установка зависимостей
python -m pip install -r requirements.txt

# Запуск тестов
python -m pytest -q

# Демо
python demo.py

# REST API (требует аутентификации)
export AIOS_API_KEYS='{"local-dev-key":{"subject":"dev","roles":["admin"]}}'
python run_rest_api.py --host 127.0.0.1 --port 8000 --db ./aios.sqlite

# Health check
curl http://localhost:8000/health
```

## Docker (рекомендуется)

```bash
docker-compose up -d --build
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

## Production Exploitation

```bash
# Симуляция 2 недель GA
python run_production_autopilot.py --simulate-2weeks --cycles-per-day 24 --verbose

# Daemon mode
python run_production_autopilot.py --daemon --interval 900

# Docker production
docker-compose -f docker-compose.prod.yml up -d --build
```

## Текущий статус

| Метрика | Значение |
|---------|----------|
| Тесты | **1010** ✅ |
| API маршруты | **143** ✅ |
| Конституция | **67 статей** ✅ |
| Платформы | OLX, Instagram, FB, TikTok, Viber, WhatsApp ✅ |
| Android milestones | M1–M8 ✅ |
| SDK | v4.2.0 ✅ |
| Marketplace | v2 ✅ |
| Production simulation | 14д / 3 профиля / 0 банов / 93.3% success ✅ |

## Лицензия и безопасность

Перед развёртыванием ознакомьтесь с [SECURITY.md](SECURITY.md) и [отчётом аудита](SECURITY_AUDIT_REPORT.md).
