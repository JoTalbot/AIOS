# AIOS Platforms — архитектура для 10000+ маркетплейс-приложений

Документ описывает, как AIOS организует работу с произвольным числом
приложений, аналогичных OLX (доски объявлений, маркетплейсы), и с
произвольным числом аккаунтов (профилей) в каждом из них.

## Модель: платформа → профили

```
┌──────────────────────────────────────────────────────────────┐
│ PlatformDescriptor (реестр платформ)                          │
│   name, android_package, agent_module,                        │
│   storage_factory, adb_factory, locale ...                    │
├──────────────────────────────────────────────────────────────┤
│ Profile (аккаунт платформы) = ключ "platform:name"            │
│   device_serial  ──► устройство/эмулятор из пула              │
│   db_path        ──► изолированное SQLite-хранилище           │
│   android_user   ──► multi-user на общем устройстве           │
│   is_default     ──► профиль по умолчанию платформы           │
└──────────────────────────────────────────────────────────────┘
```

- **Платформа** — приложение и его агентская логика (парсеры, коллектор,
  мессенджер). Реестр открыт: `register_platform()` добавляет новую
  платформу без изменения существующего кода (Open/Closed).
- **Профиль** — один аккаунт. Всё состояние аккаунта изолировано в
  собственном файле `data/<platform>/<profile>.sqlite`. Перекрёстного
  смешивания данных между аккаунтами нет по построению.

## Почему SQLite-на-профиль, а не одна большая БД

| Требование при 10000+ приложений | Решение |
|---|---|
| Изоляция аккаунтов (безопасность, бан-риски) | отдельный файл на профиль |
| Масштабирование запусков | планировщики запускаются per-profile процессами |
| Резервное копирование/перенос | файл профиля копируется целиком |
| Отказоустойчивость | повреждение БД одного профиля не задевает остальные |
| Шардинг по серверам | профили раскладываются по хостам как файлы |

Реестр профилей (`AIOS_PROFILES_DB`, по умолчанию `data/profiles.sqlite`)
только маршрутизирует — самих данных объявлений в нём нет.

## Разрешение контекста (одинаково в CLI и API)

1. явный выбор: `--profile work` / `?profile=work` (или `--db path` в CLI,
   который вообще обходит реестр);
2. переменная окружения `AIOS_PROFILE`;
3. профиль по умолчанию платформы из реестра;
4. встроенный эфемерный `default` — ровно прежнее поведение
   однопрофильной установки (`olx_ads.sqlite`), то есть существующие
   инсталляции ничего не замечают.

## CLI

```bash
# Реестр платформ и профилей
aios platforms
aios profiles add --platform olx --name work --device emulator-5556 --default
aios profiles add --platform olx --name home --device emulator-5558
aios profiles list --platform olx
aios profiles set-default --platform olx --name home
aios profiles show|remove --platform olx --name home

# Все olx-команды принимают --profile (и как раньше --db):
aios olx collect --query "лобове скло" --profile work
aios olx stats --profile home
aios olx autowatch --profile work          # ночной цикл от имени work

# Пакетные запуски по всем профилям (cron):
for p in $(aios profiles list --platform olx | jq -r '.[].name'); do
  aios olx autowatch --profile "$p" --webhook "$TG_WEBHOOK"
done
```

## REST API

Реестр:

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/api/v1/platforms` | список зарегистрированных платформ |
| GET | `/api/v1/profiles?platform=olx` | список профилей |
| POST | `/api/v1/profiles` | регистрация профиля |
| GET/DELETE | `/api/v1/profiles/{platform}/{name}` | показ/удаление |
| POST | `/api/v1/profiles/{platform}/default` | назначить дефолт |

Рабочие маршруты модулей остаются прежними, плюс профиль через
query-параметр: `GET /api/v1/modules/olx/ads?profile=work`.
Неизвестный профиль — HTTP 400. Профильные хранилища кэшируются
в памяти процесса.

**Осознанные границы текущей версии:** фоновый планировщик сбора и
мессенджер/коллектор внутри API-процесса остаются на дефолтном профиле —
per-profile фоновые работы запускаются через CLI/cron отдельными
процессами (это и есть рекомендуемая схема эксплуатации: один процесс
планировщика на профиль, устройства не делятся между профилями).

## Устройства и профили

Профиль закрепляется за устройством (`device_serial`): ADBController
формирует все команды как `adb -s <serial> ...`, поэтому эмуляторы
работают параллельно и не мешают друг другу. На одном физическом
устройстве несколько аккаунтов возможны через `android_user` (work
profile / multi-user Android) — поле зафиксировано в модели.

## Пул устройств (DevicePool)

Реализован в `aios_core/platforms/devices.py`. Одно устройство обслуживает
ровно один профиль в каждый момент времени (защита аккаунтов от
перекрёстных сессий). Хранилище пула: ``data/devices.sqlite``
(``AIOS_DEVICES_DB``; в API-процессе — ``:memory:``, если env не задан).

- ``register/heartbeat`` — реестр и живость;
- ``lease(profile_key, serial=None, profile_store=None)`` — идемпотентная
  аренда (повторная аренда профиля продлевает его же устройство), выбор
  наименее недавно использованного idle, опциональная синхронизация
  ``device_serial`` в реестр профилей;
- ``release`` / ``reap_stale`` — возврат в пул и перевод молчащих
  устройств в offline с освобождением их аренд.

CLI: `aios devices register|list|lease|release|heartbeat|reap`
(lease с `--sync` пишет serial в реестр профилей).
REST: `GET /api/v1/devices`, `POST /api/v1/devices/register|lease|
release|heartbeat|reap` (lease всегда синхронизирует реестр профилей).

## YAML-каталог платформ (реестр как данные)

Реализован в `aios_core/platforms/catalog.py`: `load_catalog("platforms/")`
читает все `*.yaml` и регистрирует платформы из файлов — код не нужен.
Эталон: `platforms/olx.yaml`. Спека: `name` + `android_package`
(обязательные), `storage_class`/`adb_class` (dotted-пути фабричных
классов), `agent_module`, `default_locale`, `description`,
`legacy_default_db`. Повторная регистрация имени переопределяет
дескриптор — обновление конфигурации без рестарта.

## MCP

Все MCP-инструменты OLX (`olx_market_stats`, `olx_listing_recommend`,
`olx_price_drops`) принимают необязательный параметр `profile` —
хранилище разрешается тем же `resolve_profile()` из реестра
(`AIOS_PROFILES_DB`) и кэшируется по имени.

## Scaffold: кодогенерация новой платформы

Реализовано (`aios_core/platforms/scaffold.py`):
`aios platforms scaffold --name prom-ua --package ua.prom.app` создаёт
`platforms/<name>.yaml`, модуль `aios_core/modules/<name>/` (хранилище —
наследник OLXStorage: вся схема доступна сразу) и smoke-тест. Парсеры/
коллекторы калибруются под приложение позже, но платформа уже регистрируется
из каталога и работает в CLI/REST/устройствах. `--dry-run` — только план.

## Fleet: автоматическое обеспечение профиля устройством

`aios_core/platforms/fleet.py`:

- `ensure_device(profile_key, pool, ...)` — аренда из пула; при нехватке
  устройств создаёт AVD (`avdmanager`), запускает headless-эмулятор, ждёт
  загрузку, регистрирует serial в пуле и арендует его. Все побочные
  эффекты — инъецируемые функции (тесты без Android SDK).
  CLI: `aios devices ensure --profile olx:work`.
- `PoolMonitor` — демон heartbeats: опрос `adb devices` → heartbeat за
  живые серийники + периодический `reap_stale`.
  CLI: `aios devices monitor [--interval N] [--once]`
  (`--once` — формат для cron/systemd-timer).

## Generic module surfaces (descriptor-driven REST)

Любая платформа из реестра автоматически получает data-plane (storage
factory дескриптора + `?profile=` как у OLX, кэш по `platform:profile`):

| Метод | Путь |
|---|---|
| GET | `/api/v1/modules/{platform}/ads?query=&limit=&profile=` |
| POST | `/api/v1/modules/{platform}/ads/ingest` (AdCard JSON) |
| GET | `/api/v1/modules/{platform}/stats?query=` |
| GET | `/api/v1/modules/{platform}/ads/{fingerprint}/history` |
| GET | `/api/v1/modules/{platform}/own` |
| POST | `/api/v1/modules/{platform}/own/snapshot` |

Статические роуты OLX зарегистрированы раньше и матчатся первыми, то есть
поведение OLX не меняется; неизвестная платформа → 404. Парсинг экрана
остаётся платформенно-специфичным (калибровка), а ingest — общий вход
для внешних коллекторов.

## Квоты пула

`DevicePool.set_limit(key, value)`: `max_devices` (регистраций всего),
`max_busy:<platform>` (одновременных аренд платформы — продление своей
аренды квоту не расходует), `max_avds` (потолок auto-созданных AVD в
`ensure_device`, по умолчанию 8). CLI: `aios devices limits [--set k=v]`;
REST: `GET|POST /api/v1/devices/limits`, превышение на register → 400.

## cron-plan: автоматизация расписаний

`aios cron-plan [--platform olx] [--interval 15] [--webhook URL]
[--write /etc/cron.d/aios]` генерирует crontab: строка per-profile
`olx autowatch` + строка `devices monitor --once`, с env-переменными
и per-profile логами. Профили читаются из реестра, поэтому план всегда
актуален текущему составу аккаунтов.

## Waitlist аренды (очередь с приоритетами)

`DevicePool.enqueue(profile_key, priority)` — идемпотентная очередь
ожидания устройства (priority DESC → FIFO). Обслуживание автоматическое:
`release()` и `reap_stale()` вызывают `serve_waitlist()`; платформенные
квоты (`max_busy:<platform>`) удерживают очередь. CLI:
`aios devices lease --enqueue --priority N | enqueue | waitlist |
cancel-wait`. REST: lease с `{"enqueue": true}` → 202 Accepted,
`GET /api/v1/devices/waitlist`, `POST .../waitlist/cancel`.

## Шардинг (ShardRouter)

`aios_core/platforms/shards.py`: профили адресуются
`host/platform/name`, маршрут назначается rendezvous-хэшированием
(HRW: max sha256(host|profile_key)) и липкий — хранится в SQLite
(`AIOS_SHARDS_DB`), перевыбор только при болезни/удалении хоста
(`set_healthy`/`remove_host` → автоматическая миграция). CLI:
`aios shards add|list|remove|route|unroute`. REST: `/api/v1/shards*`.

## Авто-scaffold из APK

`inspect_apk(path)` разбирает `aapt dump badging` → пакет, метка,
launchable-activity, target SDK; `scaffold_from_apk()` строит черновой
дескриптор и скелет платформы (candidate_name = последний сегмент
пакета). CLI: `aios platforms from-apk app.apk [--name X] [--dry-run]`.
Дальше: кандидаты resource-id для парсеров из UI-дампов калибровки.

## Дальше (дорожная карта к 10000+)

1. **REST-шлюз шардинга**: проксирование `/modules/<platform>/*` на
   хост из ShardRouter.route_for; health-probe хостов демоном.
2. **Калибровочный агент**: из UI-дампа новой платформы находит
   маркеры карточек/цен и дописывает дескриптор автоматически.
