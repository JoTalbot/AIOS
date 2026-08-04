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
| `skill.run` | device + companion (+ confirm у skill) | Выполнить декларативный skill из `skills/phone/` |
| `skill.list` | — | Список phone-skills и ошибки загрузки |
| `plan.run` | device + companion + confirm | Цель на русском → LLM-план из skills → выполнение |
| `vision.tap` | device + companion + confirm | Тап по элементу, найденному VLM по описанию `hint` |
| `react.tick` | — | Один цикл оценки уведомлений по правилам |
| `react.rules` | — | Список правил реакций и состояние дедупликации |

## Reaction engine (этап 4)

Цикл демона каждые 30с забирает уведомления Companion и применяет правила из
`phone_reactions/*.yaml`:

```yaml
id: bank_income_alert
title: "💰 Поступление на карту"
match:
  package: [ua.privatbank.ap24, ua.com.abank]
  text_regex: "(поповн|зарах)"      # regex идёт по МАСКИРОВАННОМУ тексту
action:
  type: telegram                     # telegram | enqueue | event
  template: "💰 <b>{label}</b>: {text}"
autonomy: alert_only                 # alert_only | draft | auto
cooldown_seconds: 120
```

**Действия:** `telegram` — алерт владельцу (ключи из `.env`, HTML-экранирование);
`enqueue` — задача в очередь с шаблонными payload; `event` — запись в журнал;
`llm_enqueue` — LLM-черновик (текст `{draft}` из LLMBalancer) → задача +
Telegram-уведомление с id для одобрения.
**Автономия:** `alert_only` — только алерты; `draft` — задача приходит БЕЗ confirm
и останавливается в `need_confirm` (черновик на одобрение); `auto` — с confirm.
**Дедуп** по hash уведомления + per-rule cooldown; состояние —
`reactions_state.json`. OTP и номера карт в алертах/журнале только в виде `••••`
(тест `test_event_action_has_no_text` это гарантирует).

### Одобрение черновиков (полный цикл автономии)

```
правило llm_enqueue → LLM-черновик → задача (без confirm)
→ need_confirm при исполнении → Telegram «Черновик #N … confirm N»
→ владелец: python run_phone_brain.py confirm N   (или POST /jobs/<id>/confirm)
→ задача выполняется с confirm=true
```

`confirm_job` идемпотентен и работает из статусов `need_confirm` и `queued`
(одобрение успевает до исполнения). Из терминальных — отказ.
CLI: `run_phone_brain.py confirm <id>`; API: `POST /jobs/<id>/confirm`;
для программного вызова — `queue.confirm` job с `{"id": N}`.

### Команды бота (батч B)

Текстом в Telegram-боте (от владельца):

- **«мозг»** — статус демона: версия, аптайм, занятая задача, счётчики
  очереди, устройство (онлайн/офлайн, backoff), число правил реакций.
- **«черновики»** — список задач `need_confirm` с действием и подсказкой
  «подтверди N» (подсказка указывает на самый свежий черновик).
- **«подтверди N»** (также «подтвердить N», «підтверди N») — одобрение
  черновика через `POST /jobs/<id>/confirm`.

При недоступном демоне бот честно отвечает «Phone Brain недоступен»,
не падая. Обработчик: `_handle_phone_brain_intent` рядом с мостом
(коммит моста `1c24a479`), прямой вызов API — `_phone_brain_api_request`.

API: `GET /reactions` — правила и состояние.

## LLM + VLM (этап 3)

**Планировщик** (`plan.run`): цель владельца собирается LLM (существующий
`LLMBalancer`, только импорт) в цепочку skills с параметрами. Валидация плана:
только известные skills, все объявленные `params`, ≤ 3 шагов, строковые значения.

```bash
python run_phone_brain.py enqueue plan.run \
  '{"goal":"напиши маме в WhatsApp что я задержусь на час"}' --confirm
```

**Самовосстановление селекторов**: шаг skill'а с `heal: true` + `heal_hint: "..."`
при полном падении fallback-цепочки идёт в VLM: скриншот → Gemini API
(fallback: OpenRouter) → координаты элемента → тап → запись `learned.center`
в `skill_stats.json`. Следующие запуски сначала ищут живой узел рядом с
выученной точкой (±90px) и VLM больше не вызывают. События `skill_heal` — в
журнале, файл скриншота остаётся локально.

**`vision.tap`** — ручной VLM-тап: `{"hint":"кнопка поиска", "confirm":true}`.

Конфиг (`phone_brain_config.json` → секция `vision`):
`enabled`, `gemini_model` (default `gemini-2.0-flash`),
`openrouter_model` (default `google/gemini-2.0-flash-001`).
Ключи читаются из env / `data/.llm_keys.json` (как у llm_balancer).

## Skill-движок (этап 2)

Сценарии управления телефоном — YAML/JSON-файлы в `skills/phone/`:

```yaml
id: whatsapp_open_chat
title: "WhatsApp: открыть чат"
confirm: true                 # нужен payload {"confirm": true}
sensitive: false
steps:
  - id: open_app
    do: app.open
    package: com.whatsapp
  - id: open_search
    do: ui.tap
    timeout: 5
    selectors:                # упорядоченная fallback-цепочка
      - {resource: "com.whatsapp:id/menuitem_search"}
      - {desc_contains: "Поиск"}
      - {desc_contains: "Search"}
  - id: type_contact
    do: ui.type
    text: "${contact}"        # подстановка из payload.params
```

**Глаголы шагов:** `app.open`, `ui.wait`, `ui.tap`, `ui.type` (клипборд+paste,
кириллица-безопасно), `ui.key`, `wait`, `verify` (selectors или foreground-пакет).
Флаг шага `optional: true` — ошибка превращается в пропуск.

**Селекторы** (комбинируемые ключи): `text`, `text_contains`, `desc`, `desc_contains`,
`resource` (точное или суффикс `:id/...`), `label` (text или desc), `bounds` (±24px).

**Память селекторов** (`data/android_gateway/skill_stats.json`): движок помечает,
какой индекс цепочки реально сработал (`last_good`) и при следующих запусках
проверяет его первым. Падающие цепочки накапливают `fail`-счётчики — сигнал
для LLM-восстановления (этап 3). Текст экрана наружу не выходит: только id шагов
и типы селекторов.

```bash
python run_phone_brain.py enqueue skill.list
python run_phone_brain.py enqueue skill.run \
  '{"skill":"whatsapp_open_chat","params":{"contact":"Мама"}}' --confirm
```

Битый skill-файл не мешает остальным: виден в `skill.list` с текстом ошибки.
Изменённые файлы подхватываются `skill.list` без рестарта (reload), а выполнение
использует кэш до `engine.reload()`.

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
