# Phone Brain — умный демон Android-шлюза (этап 1)

Единый процесс-«мозг» вместо разрозненных таймеров и subprocess-вызовов шлюза.

## Что даёт

| Было | Стало |
|------|-------|
| Каждая команда = новый процесс Python, гонки за экран между ботом и таймерами | Очередь задач в SQLite, единственный исполнитель, аренда (lease) |
| Watchdog спамит `adb connect` каждые 30 с (и считает «Connection refused» успехом) | Супервизор: экспоненциальный backoff 30с→15м, probe после connect, эскалация при долгом offline |
| Нет истории и диагностики джобов | Статусы/результаты каждой задачи, счётчики, журнал событий JSONL |
| Логика подтверждений размазана по CLI | Гейты confirm/device/companion — middleware исполнителя |

## Компоненты

```
aios_core/phone_brain/
├── common.py       — время/атомарный JSON (канонические хелперы, без дублей)
├── queue_store.py  — SQLite (WAL): enqueue/claim/complete/fail(backoff)/defer/dedup/cancel/purge
├── device.py       — DeviceSupervisor: reconnect+probe, backoff, circuit breaker Companion
├── handlers.py     — Executor + реестр типов задач (BUILTIN_HANDLERS)
├── events.py       — журнал событий (основа будущего reaction engine)
├── api.py          — HTTP API 127.0.0.1:8790 (stdlib)
└── daemon.py       — supervisor_loop + worker_loop + api, SIGTERM-graceful
run_phone_brain.py  — CLI
```

## Типы задач (kind)

| kind | Гейты | Описание |
|------|-------|----------|
| `device.connect` | — | Reconnect ADB с проверкой probe |
| `device.status` | — | Состояние устройства/Companion |
| `gateway.cli` | — | Read-only команды legacy CLI (`status`, `apps`, `profiles`, `notifications`, `ui-dump`, `screenshot`…) |
| `ui.screenshot` | device | Скриншот экрана |
| `ui.snapshot` | device + companion | UI-дерево; `include_text:true` требует `confirm:true` |
| `app.open` | device + confirm | Открыть приложение (package/profile) |
| `notify.collect` | device + companion | Сбор уведомлений в инбокс |

## Статусы задачи

`queued → running → done | failed | need_confirm | cancelled`;
`defer` возвращает в `queued` без сжигания попытки (лимит отложений защищает от вечного цикла);
`fail` с повтором — экспоненциальный backoff `base·2^(attempts-1)`, потолок 15 мин.

## API (127.0.0.1:8790)

```
GET  /health                 состояние демона + устройства + очереди
GET  /metrics                счётчики и метрики очереди
GET  /kinds                  типы задач и их гейты
GET  /jobs?status=&limit=    список задач
GET  /jobs/<id>              детали задачи
POST /jobs                   {kind, payload, priority?, dedup_key?} → 201
POST /jobs/<id>/cancel       отмена в очереди
POST /device/connect         приоритетный reconnect (dedup)
GET  /events?limit=          журнал событий
```

## CLI

```bash
source /opt/aios/.venv/bin/activate
python run_phone_brain.py status            # health (API или файлы состояния)
python run_phone_brain.py enqueue device.status
python run_phone_brain.py enqueue app.open '{"profile":"whatsapp"}' --confirm
python run_phone_brain.py list --status queued -n 10
python run_phone_brain.py show 42 && python run_phone_brain.py cancel 42
python run_phone_brain.py kinds | metrics | events
```

## Конфигурация

`data/android_gateway/phone_brain_config.json` (все поля опциональны):

```json
{
  "poll_interval": 10, "worker_interval": 2, "defer_seconds": 30,
  "api":    {"host": "127.0.0.1", "port": 8790},
  "queue":  {"retry_base_seconds": 20, "retry_cap_seconds": 900, "lease_seconds": 180,
             "default_max_attempts": 3, "retention_days": 7, "defer_limit": 20},
  "device": {"min_interval": 30, "max_interval": 900, "escalate_after_seconds": 600}
}
```

## Сервис

```bash
systemctl status aios-phone-brain.service
journalctl -u aios-phone-brain.service -f      # stdout
tail -f logs/phone_brain.log                   # файл (ротация 3×1МБ)
```

Старый watchdog `aios-android-gateway.service` выключен — его функцию выполняет
супервизор (возврат при необходимости: `systemctl enable --now aios-android-gateway.service`).

## Совместимость

* `health.json` обновляется в прежней схеме — `run_ops_health.py`, метрики телефона и бот не ломаются.
* Legacy CLI `run_android_gateway.py` работает как раньше (единая точка — только новые задачи).
* Миграция бота: вызовы `_android_gateway_run(...)` постепенно заменяются на `POST /jobs` / `GET /jobs/<id>`.

## Дальнейшие этапы

2. **Skill-движок** — декларативные YAML-сценарии с fallback-селекторами.
3. **LLM-планировщик + VLM** — цель → план; экран через скриншот; самовосстановление селекторов.
4. **Reaction engine** — правила на события (уведомления банков/OLX → действия).
