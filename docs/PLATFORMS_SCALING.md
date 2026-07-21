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

## ShardGateway + ShardHealthMonitor

`aios_core/platforms/gateway.py`:

- `ShardGateway.proxy(profile_key, method, path, ...)` — HTTP-хоп на
  хост профиля по липкому маршруту; если маршрут ведёт на этот узел
  (`AIOS_HOST_ID`), HTTP-петли нет — маркер `local` (клиент вызывает
  локальный роут). REST: `POST /api/v1/shards/gateway`
  `{profile, method, path, params?, body?}`.
- `ShardHealthMonitor` — демон probe `GET <base_url>/health` по всем
  хостам → `set_healthy`; больные хосты теряют маршруты автоматически.
  CLI: `aios shards monitor [--interval N] [--once]`.

## Калибровочный агент (parser_hints)

`CalibrationAdvisor.analyze(ui_dump)` ищет в дампе поисковой выдачи
повторяющиеся контейнеры, содержащие цену (распознаётся общим
`parse_price`) и заголовок, → кандидатские resource-id маркеры карточек
+ сводка по валютам. CLI:

```bash
aios platforms calibrate --platform slando --dump screen.xml [--write]
```

`--write` вливает готовые подсказки в `extras.parser_hints` дескриптора
`platforms/<name>.yaml`; дальше генератор парсера читает их из каталога.
`PlatformDescriptor.extras` — свободное расширение дескриптора.

## ParserGen: компиляция парсера из parser_hints

`aios_core/platforms/parsergen.py` замыкает петлю «калибровка →
парсер» — OLX `CardParser` хранит маркеры как **атрибут класса**
`CARD_RESOURCE_MARKERS`, поэтому платформенный парсер = подкласс с
переопределёнными маркерами, вся классификация текстов карточки
(цена/дата/ТОП/город) унаследована:

- `extract_markers(hints)` — `com.demo:id/adCard` → `adcard`
  (substring, lowercase, дедупликация);
- `build_parser(hints)` — runtime-экземпляр парсера из словаря
  подсказок без файлов (для verify-шагов и REST);
- `write_parser(name, hints, overwrite=False)` — codegen
  `aios_core/modules/<module>/card_parser.py` + идемпотентный импорт в
  `__init__.py` (маркер `codegen: parser_hints`); отказ при пустых
  маркерах/чужом модуле/существующем файле без `overwrite`;
- `parser_for(name, directory)` — парсер прямо из YAML-дескриптора
  каталога (коллектор работает сразу после `calibrate --write`).

CLI: `aios platforms codegen --platform slando [--dry-run] [--force]`.

## Bootup: E2E-пайплайн «из APK до коллектора»

`aios_core/platforms/bootup.py` / `aios platforms bootup` — вся цепочка
одной командой, каждый шаг инъецируем для тестов, `--dry-run` без
записей на диск, повторный запуск продолжает (resume) готовый скелет:

1. **scaffold** — из APK (`aapt dump badging`, runner инъецируется) или
   из пары `--name/--package`;
2. **register** — YAML-дескриптор регистрируется в реестре;
3. **calibrate** — дамп поисковой выдачи из `--dump`, инъецированного
   `driver(package, query)` или generic-драйва по ADB (открыть
   приложение → пауза → `uiautomator dump`); падение драйва без
   устройства → шаг `skipped`, статус `scaffolded`;
4. **hints → descriptor** — `write_hints_to_descriptor()` в
   `extras.parser_hints` + перерегистрация;
5. **codegen** — `write_parser(..., overwrite=True)`;
6. **verify** — дамп разбирается свежим парсером: карточки > 0 →
   статус `ready`.

```bash
aios platforms bootup --apk slando.apk --query "велосипед" --dry-run
aios platforms bootup --name slando --package com.slando.app --dump feed.xml
```

Отчёт JSON: `{platform, android_package, status, steps: {scaffold,
register, calibrate, hints, codegen, verify}}`.

REST-эквивалент калибровки: `POST /api/v1/platforms/{platform}/hints`
`{dump | hints}` → сохраняет подсказки в runtime-дескриптор и
возвращает `parser_preview` (карточки + примеры заголовков);
персистентность в YAML — через CLI (`calibrate --write`).

## ApkFetch: сама скачивает APK

`aios_core/platforms/apkfetch.py` — обёртка над
[`apkeep`](https://github.com/EFForg/apkeep) (APKPure/Google Play/F-Droid
без аккаунта; `cargo install apkeep`):

- `fetch_apk(package, out_dir="apks", source="apkpure")` → путь к
  скачанному APK; честные ValueError, runner инъецируется;
- `resolve_apk(target, fetch=False)` — вход bootup: существующий `.apk`
  | кеш `apks/<package>*.apk` | скачивание по имени пакета при
  `--fetch`.

CLI: `aios platforms fetch-apk com.instagram.android`, в пайплайне —
`aios platforms bootup --apk com.instagram.android --fetch`.

## Secrets: учётные данные только через env

`aios_core/platforms/secrets.py`: логины/пароли аккаунтов (Instagram и
т.п.) никогда не попадают в git/БД/логи:

- `AIOS_SECRET__<PLATFORM>__<FIELD>` и профильные
  `AIOS_SECRET__<PLATFORM>__<PROFILE>__<FIELD>` (вторые приоритетнее);
- `secret()/required_secret()` — ошибки называют переменную, не значение;
- `load_secrets_file()` — `data/secrets.env` (в `.gitignore`), по
  умолчанию не затирает существующие переменные.

## Калибровка детального экрана и мессенджера

`DetailCalibrationAdvisor` (там же, `calibrate.py`) закрывает оставшиеся
экраны паттерна OLX `detail.py`/`messenger.py`:

- `analyze_detail(dump)` → price/seller-маркеры (resource-id содержит
  seller/user/avatar/author/owner), CTA «написати/message/chat/call»,
  узлы длинного описания;
- `analyze_messenger(dump)` → классы поля ввода (EditText), кнопки
  отправки (send/надіслати), пузыри сообщений (rid с повторениями);
- `merge_hints(card, detail, messenger)` — секции `detail`/`messenger`
  в общем `extras.parser_hints`.

CLI: `aios platforms calibrate --platform X --dump feed.xml
[--detail post.xml] [--messages dm.xml] --write`.

## Marker drift: регрессия верстки

`aios_core/platforms/regression.py`: приложения обновляются, resource-id
меняются — `check_platform_markers(platform, fresh_dump)` сравнивает
baseline из дескриптора со свежей калибровкой и возвращает
`ok` / `drift` (baseline-маркеры потеряны → `calibrate --write` +
`codegen --force`) / `no-baseline`. `diff_markers(old, new)` —
removed/added/kept. CLI: `aios platforms marker-check --platform X
--dump feed.xml`.

## Bootup: устройства из пула и скачивание APK

`bootup_platform(...)` расширен:

- **APK**: `fetch=True, apks_dir, apk_runner` — шаг `apk` отчёта
  (`resolved`/`fetched`/`stub` при инъецированном aapt-runner);
- **устройство для live-драйва**: `serial=` напрямую, либо `pool=` —
  аренда под ключ `<platform>:calibration` (DevicePool), авто-release
  после драйва; свободных нет → `no free device in pool`;
- драйв получает `serial` (если принимает): прямая привязка к
  эмулятору профиля.

CLI: `--fetch`, `--apks-dir`, `--serial`, `--lease` (пул из
`AIOS_DEVICES_DB`).

## Instagram: первый онбординг второй платформы

`platforms/instagram.yaml` + `aios_core/modules/instagram/` —
боевой прогон всей цепочки не на OLX. Особенность: стена логина →
`InstagramLoginDriver` (login-wall детекция, ввод env-секретов
без координат, честная ошибка при непрохождении). Пошагово:
`docs/modules/instagram/ONBOARDING.md`.

## Дальше (дорожная карта к 10000+)

Архитектурный цикл подключения платформы собран полностью: APK →
scaffold → калибровка → parser_hints → codegen → verify. Возможные
шаги дальше:

1. **Codegen detail/messenger-модулей из секций hints**: как CardParser,
   но для `detail.py`/`messenger.py` платформы (шаблоны = OLX-модули).
2. **Point-драйвы поиска по hints**: калибровщик не только анализирует
   стартовую ленту, но и сам находит строку поиска/вводит query.
3. **Расписание marker-check в cron-plan**: авто-re-calibrate +
   алёрт drift по всем платформам из каталога (`devices monitor`
   туда же).
