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

## Instagram: полный функционал второй платформы

`platforms/instagram.yaml` + `aios_core/modules/instagram/` —
боевой прогон всей цепочки не на OLX:

- `InstagramCollector` — карточки ленты/выдачи (движок OLXCollector,
  парсер из дескриптора, драйв навигации);
- `InstagramDetailParser` — детальный экран из hints-detail;
- `InstagramMessenger` — guarded Direct на общей outbox-механике OLX;
- `InstagramLoginDriver` — стена входа (env-секреты) + PointDrive
  поиска; `InstagramBootstrap.doctor()` — готовность.
- CLI `aios instagram doctor|collect|login-drive|dm-send|dm-flush|
  dm-outbox`. Пошагово: `docs/modules/instagram/ONBOARDING.md`.

## Runtime-парсеры из hints (без codegen)

`aios_core/platforms/runtime_hints.py` закрывает экраны detail и
messenger без генерации файлов — подсказки читаются из дескриптора:

- `HintDetailParser` — price/seller/CTA маркеры + shape-эвристика
  заголовка/описания; `detail_parser_for(platform)` из YAML;
- `HintSender` — драйв отправки: тап по инпуту → ADBKeyBoard → тап по
  send-маркеру (ENTER fallback), шаги в отчёте;
- `chat_list_parser_for(platform)` — OLX ChatListParser с
  инъецированными маркерами строк диалогов (теперь параметр конструктора);
- `load_hints_section()` — чтение `extras.parser_hints.<section>`.

## PointDrive: точечный поисковый драйв

`aios_core/platforms/pointdrive.py`: находит в дампе поисковый инпут
(EditText или resource-id с «search»), тапает по центру bounds (без
координатных констант), вводит запрос и ENTER → дамп выдачи.
Применим как `driver=PointDrive(adb).drive` в bootup и как post-login
шаг Instagram. В cron-plan добавлен шаблон marker-drift караула:
`aios cron-plan --with-marker-check` (закомментированные строки
`platforms marker-check` по каждой платформе каталога).

## Generic AutoWatch для любой платформы

`aios_core/platforms/autowatch.py` — цикл заботы OLX AutoWatch на
descriptor+profile проводке: хранилище/ADB из резолвера профиля,
парсер карточек по цепочке codegen-модуль → runtime hints
(`resolve_card_parser`), опциональный драйв навигации
(`--drive point|login`) перед сбором каждого запроса.

```bash
aios platforms autowatch --platform instagram --profile main \
    [--query "кросівки"] [--webhook URL] [--no-collect]
```

cron-plan генерирует generic-строки autowatch для профилей всех
не-olx платформ; для olx остаётся родная команда (совместимость).

## Guarded messenger REST plane (любая платформа)

`/api/v1/modules/{platform}/chats` (GET), `/outbox` (GET),
`/outbox/send` и `/outbox/flush` (POST): резолвится мессенджер из
`<agent_module>.messenger` (класс `*Messenger(OLXMessenger)` —
Instagram Direct подхватился автоматически); профильная изоляция по
`?profile=`, очередь по умолчанию (`auto_send` только явным флагом) —
ни один мессенджер платформы не пишет во внешний мир молча.
Платформа без messenger-модуля → честный 404 с рецептом.

## VideoCards: экстрактор видео-карточек

`aios_core/platforms/videocards.py` — для непродуктового контента
(Reels/клипы): `VideoCard` (подпись, тайм-код, просмотры/лайки,
fingerprint), `HintVideoParser` по video-маркерам калибровки
(`content_categories.video_markers`) или дефолтным reel/video/clips;
`parse_counter_text` («1 234 перегляди»/«56 вподобань»),
`video_parser_for(platform)` из дескриптора.

## Own-posts Instagram (guarded-публикация)

`aios_core/modules/instagram/own_posts.py`:

- `OwnPostsParser` — счётчики постов профиля → `to_own_ad()` для
  общего OwnAdsTracker/застой-контура;
- `PostComposer.publish(image, caption, confirm=False)` — **DRY-RUN
  план по умолчанию**; `confirm=True` исполняет: push →
  `instagram://library` deep link → текстовые тапы Next → caption →
  Share (без координатных констант; дрейф верстки = честная ошибка
  шага). CLI: `aios instagram post --image i.jpg --text "..."
  [--confirm]`, снапшот: `aios instagram own [--dump grid.xml]`.

## FleetScheduler: autowatch-циклы по пулу устройств

`aios_core/platforms/fleetsched.py`: джобы `platform/profile` бегут по
интервалам на арендованных из DevicePool устройствах; last_run в kv
пула; занято → `skipped-busy` (без штамповки интервала); ошибка джоба
изолируется с гарантированным release; вернувшийся
`marker_status: "drift"` → webhook-алёрт `marker-drift`. CLI:
`aios devices fleet-run --every-s 900 [--query Q] [--webhook URL]`.

## Категории контента в калибровке

`CalibrationAdvisor.analyze` дополнительно возвращает
`content_categories`: video/reels-маркеры, story/highlight-маркеры и
счётчик duration-меток (`0:32`) — Reels/Stories-форматы без цены не
теряются при калибровке платформ с непродуктовой лентой.

## ReelsCollector: scroll-цикл видео-ленты в storage

`platforms/reelscout.py` — generic коллектор Reels/клипов любой
платформы каталога. Цикл «дамп → `HintVideoParser` → свайп» собирает
уникальные видео-карточки до лимита (`max_cards`/`max_swipes`) или пока
`stop_after_empty` дампов подряд не дадут новых (честный конец ленты).
Парсер резолвится из `content_categories.video_markers` дескриптора
(дефолт reel/video/clips), опциональный `driver(adb)` открывает
видео-вкладку — его отказ честный `RuntimeError`.

Ключевое: видео-карточки **не** попадают в таблицу объявлений — для
дедупликации между циклами в схему storage добавлены generic receipts
`olx_seen` (`check_and_record(fingerprint, kind="video")`,
`seen_count`): второй цикл по той же ленте даёт 0 нового, статистика
объявлений не загрязняется. CLI: `aios instagram reels [--db --max
--serial --directory]`.

## Instagram autopilot: полный цикл одной командой

`aios instagram autopilot` собирает весь интервальный цикл профиля в
один JSON-отчёт (`steps`): сбор карточек → Reels → Direct outbox-flush
→ опциональная guarded-публикация (`--post-image/--post-text`,
DRY-RUN без `--confirm`; login-wall pre-drive по `--login`). Guarded-
философия сохранена полностью: Direct уходит только из одобренной
очереди, публикация — только с явным подтверждением.

`aios cron-plan` для instagram-профилей генерирует строку
`instagram autopilot --login --db data/instagram-<profile>.sqlite`
(прочие платформы — generic `platforms autowatch`, OLX — родной
`olx autowatch`, как раньше).

## Multi-account: e2e через waitlist

Сквозной тест `test_multi_account_instagram_waitlist_e2e`
(`tests/test_reels_autopilot.py`) фиксирует контракт масштабирования
аккаунтов на одну ноду: два instagram-профиля в очереди
FleetScheduler'а за одним устройством — при занятости честный
`skipped-busy` обоим, после release оба отрабатывают последовательно
на одном serial, `fleet:last_run:<platform>:<profile>` пишется
раздельно, повторный запуск — строго по истечении `every_s`.

## ReelsTabDriver: калибруемый тап по видео-вкладке

`platforms/reelscout.py` дополнен `ReelsTabDriver` — драйвом открытия
вкладки Reels перед scroll-циклом (аналог login-драйва для стены входа).
Маркеры — из секции `extras.parser_hints.navigation.reels_tab`
YAML-дескриптора (`rid_markers`/`text_markers`), дефолт — типовые rid
reels/clips и подписи «Reels»; узел ищется с bounds, тап — по центру,
честный `False` без silently-координат. Резолвер
`reels_driver_for(platform, directory)` — в том же стиле, что
`video_parser_for`/`detail_parser_for` (нет секции → дефолты; нет
дескриптора → ValueError). CLI: `--open-tab` у `instagram reels` и
`instagram autopilot`; вкладка не найдена → честная ошибка
`driver не смог открыть видео-ленту` (RuntimeError отдаётся JSON-ом).

## Видео-алёрты (video-new)

`ReelsCollector` принимает `notifier` (WebhookNotifier): событие
`video-new` уходит только когда цикл принёс **новые** карточки
(`check_and_record` kind="video"), payload — platform/new/seen/query/
sample-заголовки (топ-3). Повторный цикл по той же ленте алёрта не
даёт (дедуп receipts). CLI: `--webhook URL` у `instagram reels` и
`instagram autopilot` (флаг `notified` в отчёте).

## Multi-host cron-plan (--shard-map)

`aios cron-plan --shard-map` группирует cron-строки профилей по
липким HRW-маршрутам `ShardRouter` (тот же `AIOS_SHARDS_DB`, что и
`aios shards`): заголовки `# === host: worker-1 (base_url) · профилей:
N ===`; немаршрутизированные/без живых хостов — в группе `local —
без маршрута; запускать на этом хосте`; pool-monitor помечается
«запускать на каждом хосте». Один crontab-файл раздаётся по нодам —
sticky-маршруты гарантируют, что профиль не дублируется на двух хостах.

## Автокалибровка navigation (reels_tab)

`DetailCalibrationAdvisor.analyze_navigation` из дампа домашнего экрана
сам находит tab-bar (rid `tab_bar`/`bottom_nav`/`navigation_bar`),
перечисляет вкладки и распознаёт видео-вкладку (reel/clips/video в rid
или подписи) → секция `navigation.reels_tab` для ReelsTabDriver без
ручной разметки. Честные диагнозы: «tab-bar есть, видео-вкладка не
распознана» / «tab-bar не найден» (→ дефолтные маркеры драйва). CLI:
`aios platforms calibrate --navigation home.xml [--write]`
(merge_hints принимает navigation=..., обратная совместимость).

## Own-posts в autopilot

Флаг `--own` у `instagram autopilot` добавляет шаг снапшота
собственных постов (OwnPostsParser → OwnAdsTracker в общую схему
own_ads): `--own-dump grid.xml` для явного дампа либо честная ошибка
без живого экрана (`--own-dump` в подсказке). Алёрт `own-posts` в
webhook при новых постах и негативных дельтах счётчиков (views/
favorites упали — теневой бан/удаление), `notified` в отчёте.

## ShardExec: pull-модель джобов (`platforms/shardexec.py`)

Альтернатива crontab для multi-host: `ShardJobs` — очередь
`shard_jobs` в той же AIOS_SHARDS_DB (enqueue/list/pending_for/
claim_next/complete); `claim_next(host)` отдает джобу только ноде,
на которую указывает sticky HRW-маршрут профиля — двойной запуск
на двух хостах исключён (чужая нода получает честный `None`/idle).
`ShardJobWorker.work_once()` изолирует ошибки handler'а (failed с
текстом, соседи не страдают); встроенный вид `autopilot` — guarded
shell-out в `aios instagram autopilot --login`. CLI:
`aios shards enqueue --profile ig:main --kind autopilot`,
`aios shards jobs [--status]`, `aios shards work --host X [--once]`.

## Job lease TTL и метрики очереди

ShardExec закалён под реальные отказы: `heartbeat(host)` пишется
воркером на каждом `work_once`; `requeue_stale(ttl)` возвращает в
pending claimed-джобы, зависшие дольше TTL (host снимается, маршрут
переоценится); `stats()` — глубина очереди, счётчики по статусам,
число зависших claim'ов и карта heartbeat'ов. CLI:
`aios shards jobs --stats [--ttl 600]`, `aios shards requeue-stale`.

## Встроенные виды джоб

`default_handlers` теперь покрывает основной эксплуатационный набор:
`autopilot`, `reels` (--open-tab), `dm-flush`, `marker-check` (дамп
`data/marker-<platform>.xml`). Все — shell-out в aios_cli с наследуемой
guarded-семантикой; payload.args добавляет флаги.

## Human-like pacing (антибан)

`platforms/pacing.py`: `Pacer` — рандомизированный jitter перед
действием (seed-able), квота actions/hour (скользящее окно) и лимит
длины сессии; исчерпание — честный стоп цикла (`before_action` →
False), не обход. Встроен в OLXCollector (тем самым в
InstagramCollector) и ReelsCollector; `pacer_from_limits` читает
per-profile квоты из pool kv (`pacing:<profile>:actions_per_hour`).
CLI autopilot: `--pace-actions N --pace-jitter S`, отчёт `pacing`.

## Own-promote (DRY-RUN)

`platforms/promote.py: promotion_plan` — план продвижения застоявшихся
постов (stagnant-анализ): очередь кандидатов, равномерный дневной
бюджет, действие boost. Промоут-флоу для платформы не реализован —
честный dry_run всегда; autopilot `--promote [--promote-budget N --promote-min-age-days D]`, webhook `promote-suggestion`.

## Onboarding wizard (`aios onboard`)

`platforms/onboard.py: onboard_package` — единый вход подключения:
resolve/fetch APK → bootup (scaffold→register→calibrate→codegen→
verify) → паспорт готовности {scaffolded, registered, hints,
codegen, verified_cards} + список next_commands (честный «needs
device» вместо silently-заглушки). CLI: `aios onboard com.example.app
[--name --fetch --dump --serial --root]`.

## Generic messenger-платформы: WhatsApp, Viber, TikTok

`platforms/hintmsg.py: HintsMessenger` — guarded-мессенджер целиком по
hints (inbox-тап deep-link/monkey, list_chats по chat/bubble маркерам
калибровки, HintSender ввод/отправка, общий outbox-контур).
Платформенный модуль = 3 тонких класса (Storage/Bootstrap/Messenger)
+ YAML-дескриптор с `extras.compliance` (autopost_allowed: false,
messenger: approval-only). Generic doctor: `platforms/doctor.py:
platform_doctor` (adb/дескриптор/hints-секции/storage/device/package).
CLI-группы `whatsapp`/`viber` (doctor/chats/dm-send/dm-flush/dm-outbox)
одним раннером; `platforms doctor/reels` — generic для любого
каталогового app (TikTok — video-first доказательство ReelsCollector).

## Pull-first автоматизация + jobs REST

`cron-plan --via-shards` генерирует enqueue-строки (`shards enqueue
--profile p:n --kind autopilot`) вместо shell-cron; платформы без
builtin-вида получают честный комментарий. REST-плоскость очереди для
dashboard: `GET/POST /api/v1/shards/jobs`, `GET /api/v1/shards/stats`.

## Дальше (дорожная карта к 10000+)

1. **Job-lease TTL**: повторная выдача claimed-джоб, зависших на
   умершей ноде (heartbeat + requeue), метрики глубины очереди.
2. **Встроенные виды джоб**: `reels`, `dm-flush`, `marker-check`
   по образцу autopilot из `default_handlers`.
3. **Own-promote → autopilot**: guarded-решение продвижения поста
   по stagnant-анализу (DRY-RUN план бюджета, confirm вручную).
