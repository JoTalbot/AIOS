# Production Exploitation Guide

**Версия документа:** 9.2.0-production | **Дата:** 23 июля 2026

Полное руководство по промышленной эксплуатации AIOS с акцентом на Instagram-профили,
compliance, pacing и мониторинг.

---

## Архитектура Production-решения

```
┌─────────────────────────────────────────────────────────┐
│                  Production Autopilot                    │
├─────────────────────────────────────────────────────────┤
│  ProductionProfile × N                                  │
│  ├── Compliance Guard (deny-by-default)                 │
│  ├── Pacer (jitter 0.8–2.5s, actions/hour limit)       │
│  ├── Predictive Risk (record_event, risk scoring)       │
│  └── AI Advisor (draft-only, human-approve)             │
├─────────────────────────────────────────────────────────┤
│  CycleReport: success_rate, pacing, compliance, drift   │
├─────────────────────────────────────────────────────────┤
│  Prometheus Metrics → Grafana Dashboards                │
└─────────────────────────────────────────────────────────┘
```

## Профили

### Дефолтная конфигурация (3 Instagram)

| Профиль | Actions/Hour | Session Max | Jitter | Device |
|---------|-------------|-------------|--------|--------|
| ig_shop_1 | 45 aph | 30 min | 0.8–2.5s | emulator-5554 |
| ig_shop_2 | 50 aph | 30 min | 0.8–2.5s | emulator-5556 |
| ig_shop_3 | 40 aph | 25 min | 0.8–2.5s | emulator-5558 |

### Обоснование параметров

- **Actions per hour ≤50:** в пределах наблюдаемого поведения обычных пользователей IG
- **Session max 25–30 мин:** соответствует естественным сессиям
- **Jitter 0.8–2.5s:** рандомизация задержек между действиями
- **Compliance:** collect/send/autopost deny-by-default

## Compliance

Модуль `platforms/compliance.py` реализует:

- `compliance_guard` — deny-by-default для autopost, collect, send, auto_send
- Scaffold deny-блок при отсутствии compliance-флага в дескрипторе
- Compliance-метаданные в `extras.compliance.note` YAML-дескрипторов
- Audit-log: `olx_audit` для всех действий

### Compliance-флаги

```yaml
# platforms/instagram.yaml
extras:
  compliance:
    autopost: false      # deny
    collect: false       # deny
    send: false          # deny
    auto_send: false     # deny
    note: "Requires manual approval per ToS"
```

## Pacing

Модуль `platforms/pacing.py`:

```python
from platforms.pacing import Pacer

pacer = Pacer(actions_per_hour=45, jitter_range=(0.8, 2.5))
pacer.before_action()  # blocks or raises if limit exceeded
```

### CLI-параметры

```bash
python run_production_autopilot.py \
  --pace-actions 45 \
  --pace-jitter 0.8,2.5 \
  --verbose
```

## Запуск

### Симуляция (GA-доказательство)

```bash
python run_production_autopilot.py \
  --simulate-2weeks \
  --cycles-per-day 24 \
  --verbose \
  --output report.json
```

Результат: `production_simulation_report.json`
- 14 дней × 3 профиля × 4 цикла/день = 168 циклов
- Success rate ≥90%
- Bans = 0 → `ban_free: true`, `ga_met: true`

### Единичный цикл

```bash
python run_production_autopilot.py --config default_3_ig --verbose
```

### Daemon (реальная эксплуатация)

```bash
python run_production_autopilot.py \
  --daemon \
  --interval 900 \
  --config from_env \
  --verbose
```

Переменные окружения:
- `AIOS_PRODUCTION_PROFILES` — JSON-массив профилей
- `DEVICE_POOL_SIZE` — количество устройств
- `WEBHOOK_URL` — URL для уведомлений

### Docker Production

```bash
cd deploy/production
docker-compose -f docker-compose.prod.yml up -d --build
```

Компоненты:
| Сервис | Порт | Назначение |
|--------|------|-----------|
| api | 8000 | REST API (2 CPU, 2 GB) |
| autopilot | — | Daemon (interval 900s) |
| dashboard | 8080 | Web UI |
| prometheus | 9090 | Metrics collection |
| grafana | 3000 | Dashboards |

## Мониторинг

### Prometheus-метрики

```bash
curl http://localhost:8000/metrics | grep aios_production
```

Метрики:
- `aios_production_profiles` — количество профилей
- `aios_production_cycles_total` — всего циклов
- `aios_production_actions_total` — всего действий
- `aios_production_success_rate` — процент успеха
- `aios_production_bans_total` — банов
- `aios_pacer_actions{profile}` — действий по профилю

### Grafana Dashboards

**Ops Dashboard** (операционный):
- Queue depth
- Host health
- Device status
- Catalog metrics

**Production Dashboard** (продуктовый):
- Ban-free дней (stat panel)
- Profiles ≥ 3
- Success rate > 90%
- Cycles progress (336 total)
- Pacer actions vs limit
- Predictive risk
- Compliance status
- Devices online
- Последние циклы (table)

### Alerts

Файл: `deploy/monitoring/production-alerts.yml`

| Алерт | Уровень | Условие |
|-------|---------|---------|
| BanDetected | Critical | bans_total > 0 |
| LowSuccessRate | Warning (15m) | success < 80% |
| CriticalSuccessRate | Critical (5m) | success < 50% |
| HighPredictiveRisk | Warning | risk > 0.7 |
| DeviceOffline | Warning | device down |
| NoFreeDevices | Critical | pool exhausted |
| ComplianceBlocked | Warning | all blocked |
| GAProgress | Info | cycles < 336 |

## Onboarding чек-лист (≤30 минут)

- [ ] Клонировать репозиторий
- [ ] Установить зависимости: `pip install -r requirements.txt`
- [ ] Настроить API-ключи: `export AIOS_API_KEYS=...`
- [ ] Запустить тесты: `python -m pytest -q` (1010 passing)
- [ ] Создать платформу: `aios platforms scaffold --platform <name>`
- [ ] Калибровочный рецепт: `aios platforms doctor --calibrate-recipe`
- [ ] На устройстве: `aios platforms calibrate --dump /tmp/ui.xml --write`
- [ ] Сгенерировать код: `aios platforms codegen --force`
- [ ] Запустить: `aios platforms bootup --verify`
- [ ] Проверить health: `curl http://localhost:8000/health`

## Секреты и переменные окружения

```bash
# API Keys (обязательно)
export AIOS_API_KEYS='{"key":{"subject":"operator","roles":["admin"]}}'

# Production Profiles
export AIOS_PRODUCTION_PROFILES='[
  {"platform":"instagram","name":"shop_1","device_serial":"emulator-5554","aph":45}
]'

# Device Pool
export DEVICE_POOL_SIZE=3

# Webhook (Slack/Teams)
export AIOS_WEBHOOK_URL=https://hooks.slack.com/services/...

# Database paths
export AIOS_PROFILES_DB=./data/profiles.sqlite
export AIOS_EVENTS_DB=./data/events.sqlite
export AIOS_MEMORY_DB=./data/memory.sqlite
```

## Troubleshooting

### Проблема: Low Success Rate

1. Уменьшите `aph` (actions per hour)
2. Увеличьте `jitter` range
3. Проверьте compliance YAML `extras.compliance.note`
4. Проверьте predictive risk: `python run_production_autopilot.py --health`

### Проблема: Drift > 5%

```bash
# Перекалибровка
aios platforms calibrate --platform instagram --dump /tmp/ui_dump.xml --write
aios platforms codegen --platform instagram --force
aios platforms bootup --verify
```

### Проблема: Ban detected

1. **Немедленно:** остановить daemon
2. Уменьшить aph на 20%
3. Увеличить jitter до 1.0–3.0s
4. Проверить compliance YAML
5. Проверить predictive risk history
6. Перезапустить с `--pace-actions <reduced>`

## После 14 дней ban-free

```bash
# Tag GA release
git tag v9.2.0
git push origin v9.2.0
```

## API Reference

| Endpoint | Method | Описание |
|----------|--------|----------|
| `/health` | GET | Health check (public) |
| `/metrics` | GET | Prometheus metrics |
| `/api/v1/stats` | GET | Runtime statistics |
| `/api/v1/advisor/draft` | POST | AI Advisor draft |
| `/api/v1/marketplace/publish` | POST | Publish plugin |
| `/api/v1/marketplace/search` | GET | Search plugins |
| `/api/v1/devices/register` | POST | Register device |
| `/api/v1/devices/list` | GET | List devices |
| `/dashboard` | GET | Web dashboard (read-only) |

Полный список: **143 маршрута** — см. [API Reference](api.md).
