# AIOS Changelog

All notable changes to this project will be documented in this file.

## [9.3.1] — 2026-07-23

### Fixed
- Заменены bare `except:` на `except Exception:` в 6 модулях
  (`android_predictive`, `hybrid_quantum_classical`, `load_testing`,
  `migration`, `self_healing`, `test_circuit_breaker`).
- `print()` заменены на `logging` в `backup_manager.py` и
  `data_export.py`.
- `console_notification` в `monitoring.py` теперь использует
  `logger.critical` вместо `print()`.

### Improved
- `SelfHealing` (`self_healing.py`): добавлены полные docstrings,
  логирование ошибок восстановления, аннотации `Optional[Dict]`.
- `HybridQuantumClassical`: fallback на классический режим теперь
  пишется в лог с информацией об ошибке.
- `MigrationManager`: ошибка чтения таблицы миграций логируется с
  поясняющим сообщением.
- Непродуктивные f-строки без интерполяции убраны в `integration_examples`
  и `evolution_manager`.

### Documentation
- `README.md` расширен (≈340 строк): архитектурная диаграмма, описание
  проекта, prerequisites, структура проекта, пошаговый гайд «Adding a
  new platform», секция Development.
- `CONTRIBUTING.md` расширен: процессы Code Review и Release.
- `aios_cli.py`: 10 docstrings добавлены для ранее недокументированных
  функций (`_add_olx_parsers`, `_run_olx`, `_run_platforms`,
  `_run_profiles`, `_run_devices`, `_run_shards`, `main`,
  `with_db`, `driver`, `_profile_line`).

## [9.0.0] - 2026-07-21

### Added
- **Compliance-контур (H2.10)**: `platforms/compliance.py`
  (`compliance_block`/`compliance_guard`/`rate_limit_hours`) —
  ToS-флаги дескриптора принуждают guarded-действия: `autopost`
  (даже с confirm), `collect`, `send` (draft), `auto_send`
  (прямая запись на устройство только при `messenger: open`).
  Проводка: CLI-группы мессенджеров (dm-send), generic
  `platforms reels`, Instagram PostComposer; scaffold-шаблон
  выдаёт deny-by-default блок; compliance-секции добавлены в
  дескрипторы olx/instagram (autopost только с --confirm);
  per-platform `actions_per_hour`.
- **Audit-log в storage**: таблица `olx_audit` + `audit()`/
  `audit_list()`; outbox-lifecycle (enqueue/mark) пишется
  автоматически для всех платформ-наследников OLXStorage.
- **Telemetry counters (H2.9 добивка)**: `aios_seen_receipts
  {platform,kind}` и `aios_outbox_pending{platform}` из
  per-platform БД `data/*.sqlite` (read-only, чужие базы
  пропускаются); Prometheus alert-правила
  `deploy/monitoring/aios-alerts.yml` (падение агента, бэклог
  очереди, зависшие claim'ы, исчерпание пула, отставание
  одобрения outbox) + подключение в prometheus.yml.

## [9.0.0-alpha.21] - 2026-07-21

### Added
- **Calibrate-рецепт (on-device hints, H1.5)**: `platforms/recipe.py`
  (`calibration_recipe` — пошаговый сценарий ADB-дампов и
  `calibrate --write` под профиль платформы: messenger-first /
  collector / marketplace полного стека; учитывает уже закрытые секции
  и serial устройства); `platform_doctor(..., report_recipe=True)` и
  CLI `platforms doctor --platform X --calibrate-recipe`.
- **Ops-dashboard (web-pane, H2.8)**: `platforms/dashboard.py`
  (`dashboard_html` — самодостаточная read-only HTML-панель с inline
  CSS/JS: очередь джобов, статистика, пул устройств, профили,
  shard-host; данных из UI нет — guarded); REST `GET /dashboard`.
- **Facebook Marketplace onboarding-пакет (H2.7)**:
  `platforms/facebook.yaml` (com.facebook.katana, OLX-like,
  compliance collector:true/approval-only/no-autopost) +
  `aios_core/modules/facebook/` (FacebookStorage/Messenger/Bootstrap);
  CLI-группа `facebook` (doctor/chats/dm-send/dm-flush/dm-outbox);
  per-platform ONBOARDING-доки WA/Viber/TikTok/Facebook.
- **Prometheus-телеметрия (H2.9)**: `platforms/telemetry.py`
  (`fleet_snapshot` + `prometheus_metrics`: aios_shard_jobs{status},
  queue_depth, stale_claimed, shard_hosts, devices{state}, profiles,
  catalog_platforms); `/metrics` отдаёт честный plain-text;
  `deploy/monitoring/` — prometheus.yml, Grafana-dashboard JSON, README.

### Fixed
- REST `/metrics` больше не JSON-строка: секционная отказоустойчивость
  (ядро/флот независимы) + `text/plain` (Prometheus-сумісный формат).
- Brand-name маппинг CLI приведён к нужным CamelCase (Facebook).

## [9.0.0-alpha.20] - 2026-07-21

### Added
- **Onboarding wizard**: `platforms/onboard.py` (`onboard_package` —
  fetch→bootup→паспорт готовности+next_commands); CLI `aios onboard`.
- **Generic messenger-платформы**: `platforms/hintmsg.py`
  (HintsMessenger — guarded outbox/flush по calibrated hints,
  deep-link/monkey inbox, chat_markers) + `platforms/doctor.py`
  (platform_doctor чек-лист); onboarding-пакеты **WhatsApp, Viber,
  TikTok** (storage/messenger/bootstrap, yaml + extras.compliance
  approval-only); CLI-группы `whatsapp`/`viber`, generic
  `platforms doctor`/`platforms reels --platform X`.
- **Pull-first автоматизация**: `cron-plan --via-shards` (enqueue-
  строки вместо shell-cron) + REST-плоскость очереди:
  `GET/POST /api/v1/shards/jobs`, `GET /api/v1/shards/stats`.

## [9.0.0-alpha.19] - 2026-07-21

### Added
- **Job lease TTL (ShardExec)**: `heartbeat(host)` на каждом
  work_once; `requeue_stale(ttl)` возвращает зависшие claimed-джобы в
  pending (host/route переоценка); `stats()` — queue depth, счётчики,
  stale_claimed, heartbeats. CLI `shards jobs --stats`,
  `shards requeue-stale --ttl N`.
- **Встроенные виды джоб**: `default_handlers` — `autopilot`,
  `reels`, `dm-flush`, `marker-check` (guarded shell-out,
  payload.args).
- **Human-like pacing (`platforms/pacing.py`)**: `Pacer` — jitter
  (seed-able RNG), actions/hour скользящим окном, session limit;
  честный стоп циклов в OLXCollector/InstagramCollector/ReelsCollector;
  `pacer_from_limits` из pool kv; CLI `--pace-actions/--pace-jitter`,
  отчёт `pacing` в autopilot.
- **Own-promote (`platforms/promote.py`)**: `promotion_plan` — DRY-RUN
  план продвижения stagnant-постов (кандидаты, равномерный бюджет,
  boost); autopilot `--promote [--promote-budget --promote-min-age-days]`,
  webhook `promote-suggestion`.

## [9.0.0-alpha.18] - 2026-07-21

### Added
- **Автокалибровка navigation**: `DetailCalibrationAdvisor.
  analyze_navigation` — tab-bar/вкладки/reels_tab из дампа домашнего
  экрана (честные диагнозы без вкладки/bар'а); `merge_hints` принимает
  `navigation=`/`content_categories=`; CLI `calibrate --navigation`.
- **Own-posts в autopilot**: флаг `--own [--own-dump]` — снапшот
  собственных постов (OwnAdsTracker) шагом цикла; webhook-алёрт
  `own-posts` на новые посты и негативные дельты счётчиков;
  честная ошибка без живого экрана без `--own-dump`.
- **ShardExec (`platforms/shardexec.py`)**: pull-модель джобов поверх
  AIOS_SHARDS_DB — `ShardJobs` (enqueue/pending_for/claim_next/
  complete, claim только sticky-HRW нодой), `ShardJobWorker.work_once`
  с изоляцией ошибок handler'а, встроенный вид `autopilot` (guarded
  shell-out); CLI `shards enqueue/jobs/work [--host --once]`.

## [9.0.0-alpha.17] - 2026-07-21

### Added
- **ReelsTabDriver (`platforms/reelscout.py`)**: калибруемый драйв
  открытия вкладки Reels перед scroll-циклом — маркеры из секции
  `navigation.reels_tab` YAML-дескриптора (`rid_markers`/
  `text_markers`, дефолт reels/clips/«Reels»), тап по центру bounds,
  честный `False`/`RuntimeError` без silently-координат; резолвер
  `reels_driver_for(platform, directory)`. CLI `--open-tab` у
  `instagram reels` и `instagram autopilot`.
- **Видео-алёрты**: `ReelsCollector(notifier=...)` — событие
  `video-new` в WebhookNotifier при новых видео-карточках цикла
  (payload: platform/new/seen/query/sample; дедуп через receipts,
  повторный цикл — без алёрта). CLI `--webhook URL` у `instagram
  reels`/`autopilot` + флаг `notified` в отчёте.
- **Multi-host cron-plan**: флаг `--shard-map` группирует cron-строки
  профилей по липким HRW-маршрутам ShardRouter (`AIOS_SHARDS_DB`) с
  заголовками `# === host: ... ===`; немаршрутизированные профили →
  группа `local`; pool-monitor помечен «на каждом хосте».

## [9.0.0-alpha.16] - 2026-07-21

### Added
- **ReelsCollector (`platforms/reelscout.py`)**: generic scroll-цикл
  видео-ленты (Reels/клипы) любой платформы — дамп → `HintVideoParser`
  → свайп до лимита или честного конца ленты (`stop_after_empty`);
  парсер из `content_categories.video_markers` дескриптора,
  опциональный driver вкладки; CLI `aios instagram reels`.
- **Generic receipts в storage**: таблица `olx_seen`,
  `check_and_record(fingerprint, kind)` / `seen_count(kind)` — дедуп
  видео-карточек и событий между циклами без загрязнения таблицы
  объявлений (миграция бесшовная, CREATE IF NOT EXISTS).
- **`aios instagram autopilot`**: полный цикл профиля одной командой —
  collect → Reels → Direct outbox-flush → опциональный guarded-пост
  (`--post-image/--post-text`, DRY-RUN без `--confirm`; `--login`
  для pre-drive через login-стену). Cron-plan генерирует для
  instagram-профилей строки `instagram autopilot --login`.
- **Multi-account e2e**: сквозной тест двух Instagram-профилей через
  waitlist на одном устройстве (skipped-busy → последовательный
  запуск → раздельный last_run на профиль).

## [9.0.0-alpha.15] - 2026-07-21

### Added
- **Instagram own-posts**: `OwnPostsParser` (счётчики лайков/
  комментариев/просмотров → OwnAdsTracker через `to_own_ad()`) и
  `PostComposer` — guarded-публикация постов: DRY-RUN план по
  умолчанию, `confirm=True` исполняет (push → deep link → текстовые
  тапы Next/Share, без координат; честные ошибки дрейфа верстки);
  CLI `instagram own`, `instagram post --image X --text Y [--confirm]`.
- **VideoCards (`platforms/videocards.py`)**: экстрактор видео-карточек
  (Reels/клипы) — `VideoCard` (подпись/тайм-код/просмотры/лайки),
  `HintVideoParser` по video-маркерам калибровки, `parse_counter_text`,
  `video_parser_for` из дескриптора.
- **FleetScheduler (`platforms/fleetsched.py`)**: интервальные
  autowatch-джобы платформ на арендованных из DevicePool устройствах
  (last_run в kv пула; skipped-busy честно; ошибки изолированы с
  release; marker-drift webhook-алёрты); CLI `devices fleet-run`.

## [9.0.0-alpha.14] - 2026-07-21

### Added
- **Generic AutoWatch (`platforms/autowatch.py`)**: цикл заботы OLX
  AutoWatch для любой платформы каталога — profile-scoped storage/adb,
  цепочка резолва парсера (codegen-модуль → runtime hints,
  `resolve_card_parser`), драйв навигации `point|login`; CLI
  `aios platforms autowatch --platform X [--profile --query --webhook
  --drive --no-collect]`; cron-plan генерирует generic-строки для всех
  не-olx профилей.
- **Guarded messenger REST plane**: `GET /api/v1/modules/{platform}/
  chats`, `GET /outbox`, `POST /outbox/send`, `POST /outbox/flush` —
  для любой платформы с messenger-модулем (Instagram Direct сразу);
  profile-scoped, очередь по умолчанию, `auto_send` явным флагом, 404
  с рецептом для платформ без модуля.
- **CalibrationAdvisor content_categories**: video/reels-маркеры,
  story/highlight-маркеры, счётчик duration-меток (Reels/Stories без
  цены не теряются при калибровке).

## [9.0.0-alpha.13] - 2026-07-21

### Added
- **Runtime-парсеры из hints (`platforms/runtime_hints.py`)**: detail и
  messenger без codegen-файлов — `HintDetailParser` (цена/продавец/CTA +
  shape-эвристика), `HintSender` (тап инпута → ADBKeyBoard → тап
  send-маркера/ENTER, отчёт по шагам), `detail_parser_for` /
  `chat_list_parser_for` / `load_hints_section` из YAML-дескриптора.
- **PointDrive (`platforms/pointdrive.py`)**: точечный поисковый драйв —
  находит EditText/search-инпут по bounds (без координатных констант),
  вводит запрос и жмёт ENTER; самостоятельный bootup-драйв и
  post-login шаг Instagram.
- **Instagram — полный функционал**: `InstagramCollector` (движок
  OLXCollector + драйв + parser_for → InstagramStorage),
  `InstagramDetailParser`, `InstagramMessenger` (guarded Direct на общей
  outbox-механике OLX: очередь по умолчанию, `flush` после одобрения,
  Direct-inbox deep link, hints-executor), `InstagramBootstrap.doctor()`
  (готовность; значения секретов не отчитываются); `InstagramLoginDriver`
  принимает search_drive (поиск за стеной входа).
- **CLI `aios instagram`**: `doctor`, `collect [--login]`,
  `login-drive`, `dm-send` (в outbox; `--auto-send` немедленно),
  `dm-flush`, `dm-outbox`.
- **cron-plan `--with-marker-check`**: закомментированные marker-drift
  строки по каждой платформе каталога.

### Changed
- **OLX ChatListParser**: маркеры строк чата — параметр конструктора
  (обратная совместимость с OLX-маркерами по умолчанию), переиспользуется
  Instagram и другими платформами из калибровки.

## [9.0.0-alpha.12] - 2026-07-21

### Added
- **ApkFetch (`platforms/apkfetch.py`)**: автозагрузка APK через apkeep
  (APKPure/Google Play/F-Droid): `fetch_apk`/`resolve_apk` с кешем
  `apks/`; `bootup --apk <package> --fetch` скачивает APK сам;
  CLI `aios platforms fetch-apk`.
- **Secrets (`platforms/secrets.py`)**: учётные данные платформ через
  `AIOS_SECRET__<PLATFORM>[__<PROFILE>]__<FIELD>` +
  `data/secrets.env` loader; значения никогда в git/БД/логах;
  `.gitignore` расширен (`*.env`, `secrets.env`, `apks/`).
- **DetailCalibrationAdvisor**: маркеры детального экрана
  (цена/продавец/CTA/описание) и мессенджера (ввод/отправка/пузыри),
  `merge_hints` в секции `detail`/`messenger` подсказок; CLI calibrate
  `--detail`/`--messages`.
- **Marker drift (`platforms/regression.py`)**: `diff_markers` +
  `check_platform_markers` (ok/drift/no-baseline) — защита от
  обновлений верстки приложений; CLI `platforms marker-check`.
- **Bootup**: `--fetch`/`--apks-dir`/`--serial`/`--lease` — устройство
  для live-драйва из DevicePool (аренда `<platform>:calibration` с
  авто-release), serial-проброс в драйв; толерантность stub-APK при
  инъецированном aapt-runner.
- **Instagram (`com.instagram.android`)**: платформа заscaffoldена
  (каталог + модуль + хранилище), `InstagramLoginDriver` — прохождение
  стены входа через env-секреты (детекция логин-экрана, ввод без
  координат, честная ошибка при неуспехе); онбординг
  `docs/modules/instagram/ONBOARDING.md`.

## [9.0.0-alpha.11] - 2026-07-21

### Added
- **ParserGen (`platforms/parsergen.py`)**: компиляция CardParser из
  `extras.parser_hints` калибровки — `extract_markers` (resource-id →
  substring-маркеры), `build_parser` (runtime-парсер без файлов),
  `write_parser` (codegen `card_parser.py` платформы с идемпотентным
  импортом в `__init__.py`), `parser_for` (парсер прямо из YAML
  дескриптора); CLI `aios platforms codegen [--dry-run] [--force]`.
- **Bootup E2E (`platforms/bootup.py`)**: пайплайн «из APK до
  коллектора» одной командой `aios platforms bootup` — scaffold (APK
  или name/package, resume повторов) → register → calibrate (dump /
  injected driver / generic ADB-драйв) → hints в дескриптор → codegen →
  verify; `dry_run` без записей; статусы `ready` / `calibration-empty` /
  `scaffolded`.
- **REST `POST /api/v1/platforms/{platform}/hints`**: калибровка
  parser_hints по dump или прямой приём объекта; `parser_preview`
  (карточки + заголовки) свежесобранным парсером; сохранение в
  runtime-дескриптор.

### Changed
- **OLX CardParser**: маркеры карточек — атрибут класса
  `CARD_RESOURCE_MARKERS` (обратная совместимость с модульной
  константой); платформенные парсеры переопределяют маркеры подклассом.
- **CLI calibrate**: запись подсказок вынесена в общий
  `write_hints_to_descriptor()` (используется и bootup).
- **Scaffold YAML**: описание дескриптора — двойные кавычки с
  экранированием (двоеточия/спецсимволы не ломают парсер).

## [9.0.0-alpha.10] - 2026-07-21

### Added
- **ShardGateway (`platforms/gateway.py`)**: проксирование вызовов на
  хост профиля по липкому маршруту; `local`-маркер без HTTP-петли при
  маршруте на собственный узел (`AIOS_HOST_ID`); REST
  `POST /api/v1/shards/gateway`. Инъецируемый транспорт.
- **ShardHealthMonitor**: демон health-probe (`GET /health` по хостам →
  set_healthy, больные теряют маршруты); CLI `aios shards monitor
  [--once]`.
- **CalibrationAdvisor (`platforms/calibrate.py`)**: автопоиск маркеров
  карточек/цен в UI-дампе новой платформы (повторяющиеся контейнеры с
  ценой и заголовком), сводка по валютам, подсказка при пустом дампе;
  CLI `aios platforms calibrate --platform X dump.xml [--write]` —
  подсказки вливаются в `extras.parser_hints` дескриптора.
- **PlatformDescriptor.extras**: свободные расширения (parser_hints и
  далее), проброшены через YAML-каталог и to_dict.
- 11 новых тестов (`tests/test_gateway_calibrate.py`).

## [9.0.0-alpha.9] - 2026-07-21

### Added
- **Lease waitlist (`pool_waitlist`)**: идемпотентная очередь ожидания
  устройства с приоритетами (priority DESC → FIFO); автоматическое
  обслуживание при `release()`/`reap_stale()` с соблюдением
  платформенных квот. CLI `devices lease --enqueue|enqueue|waitlist|
  cancel-wait`; REST lease с `enqueue` → 202, `/devices/waitlist[/cancel]`.
- **ShardRouter (`platforms/shards.py`)**: липкий роутинг профилей по
  хостам (rendezvous hashing), персистентность в `AIOS_SHARDS_DB`,
  автомиграция при болезни/удалении хоста. CLI `aios shards
  add|list|remove|route|unroute`; REST `/api/v1/shards*`.
- **APK auto-scaffold**: `inspect_apk()` (`aapt dump badging`) +
  `scaffold_from_apk()` — черновой дескриптор и скелет платформы из APK;
  CLI `aios platforms from-apk [--name X] [--dry-run]`.
- 13 новых тестов (`tests/test_fleet_scale.py`).

## [9.0.0-alpha.8] - 2026-07-21

### Added
- **Generic module REST surfaces**: любая зарегистрированная платформа
  получает data-plane из дескриптора без кода —
  `/api/v1/modules/{platform}/ads[|/ingest]`, `/stats`,
  `/ads/{fingerprint}/history`, `/own[|/snapshot]`, с `?profile=`
  и кэшем по `platform:profile`; статические роуты OLX матчатся первыми,
  неизвестная платформа → 404.
- **Pool quotas**: `DevicePool` limits `max_devices`,
  `max_busy:<platform>` (продление аренды не расходует квоту), `max_avds`
  (потолок auto-созданных AVD в ensure_device, default 8). CLI
  `aios devices limits [--set k=v]`; REST `GET|POST /api/v1/devices/limits`.
- **`aios cron-plan`**: генерация crontab — per-profile `olx autowatch`
  + `devices monitor --once`, env и per-profile логи, `--write`.
- 7 новых тестов (`tests/test_module_generic.py`).

## [9.0.0-alpha.7] - 2026-07-21

### Added
- **Platform scaffold (`platforms/scaffold.py`)**: `aios platforms
  scaffold --name X --package ua.x.app [--dry-run]` генерирует скелет
  новой платформы — YAML-дескриптор, модуль `aios_core/modules/<name>/`
  с хранилищем-наследником OLXStorage и smoke-тест; валидация
  имени/пакета, защита от перезаписи.
- **Fleet `ensure_device` (`platforms/fleet.py`)**: профилю гарантируется
  устройство — аренда из пула или создание AVD + запуск headless-эмулятора
  + регистрация в пуле; побочные эффекты инъецируемы. Команда
  `aios devices ensure --profile olx:work`.
- **PoolMonitor**: демон heartbeats (`adb devices` → heartbeat,
  `reap_stale` → offline); CLI `aios devices monitor [--interval N]
  [--once]` (формат `--once` для cron).
- 12 новых тестов (`tests/test_fleet_scaffold.py`).

## [9.0.0-alpha.6] - 2026-07-21

### Added
- **DevicePool (`platforms/devices.py`)** — пул устройств/эмуляторов с
  арендой под профили: one-device-one-profile, идемпотентная аренда с
  выбором least-recently-used idle, heartbeats, `reap_stale` → offline с
  освобождением аренд, синхронизация `device_serial` в реестр профилей.
  CLI `aios devices register|list|lease|release|heartbeat|reap`; REST
  `/api/v1/devices*`; персистентность `data/devices.sqlite`/`AIOS_DEVICES_DB`.
- **YAML-каталог платформ (`platforms/catalog.py`)**: `load_catalog()` /
  `load_catalog_file()` регистрируют платформы из YAML (реестр как
  данные); эталон `platforms/olx.yaml`; фабрики из dotted-путей классов.
- **MCP `profile`-параметр**: `olx_market_stats`,
  `olx_listing_recommend`, `olx_price_drops` принимают `profile` и
  резолвят хранилище из реестра профилей с кэшированием.
- **ProfileStore.default()** теперь постоянный (`data/profiles.sqlite`)
  без env — профили переживают CLI-вызовы.
- 26 новых тестов (`tests/test_platforms_profiles.py`).

## [9.0.0-alpha.5] - 2026-07-21

### Added
- **Platforms & profiles architecture (`aios_core/platforms/`)** —
  масштабируемая модель «платформа → профили» для тысяч маркетплейс-
  приложений: реестр `PlatformDescriptor` (open/closed,
  `register_platform`), `Profile` (аккаунт = device_serial + изолированное
  хранилище + локаль), SQLite-реестр `ProfileStore`, единый резолвер
  (`--profile` / `?profile=` → `AIOS_PROFILE` → default реестра →
  legacy-совместимый эфемерный `default`).
- **ADBController serial binding**: все команды формируются как
  `adb -s <serial> ...` — параллельная работа эмуляторов под разными
  аккаунтами; добавлены `tap()` и `input_text()` (ADBKeyBoard).
- **CLI**: `aios platforms`, `aios profiles list|add|show|remove|
  set-default`; все `aios olx …` принимают `--profile` (явный `--db`
  обходит реестр); неизвестный профиль → чистая JSON-ошибка.
- **REST**: `/api/v1/platforms`, CRUD `/api/v1/profiles*` (+default);
  любой модульный маршрут OLX принимает `?profile=<name>` с кэшированием
  профильных хранилищ в процессе; `ValueError` → HTTP 400.
- OLXStorage создаёт дерево каталогов для profile-путей
  (`data/olx/<profile>.sqlite`).
- Документ `docs/PLATFORMS_SCALING.md` — модель, конвенции CLI/API,
  дорожная карта к 10000+ приложений (каталог дескрипторов,
  кодогенерация поверхностей, пул устройств, шардинг).
- 17 новых тестов (`tests/test_platforms_profiles.py`).

## [9.0.0-alpha.4] - 2026-07-21

### Added
- **Competitor portfolio crawl (`competitive.py`)**: `parse_seller_ads()`
  parses the "other ads by this seller" block from a detail-page dump
  (guarded by section-marker detection + viewed-ad exclusion by URL/ad-id);
  `CompetitiveWatch.observe_seller_ads()` stores the whole portfolio as
  market observations and links only ads similar to a chosen own listing
  (idempotent — re-scans create no duplicates).
- **REST**: `POST /olx/competitive/seller-scan` (`fingerprint`, `xml`,
  optional `viewed_url`/`viewed_ad_id`).
- **CLI**: `aios olx competitive-seller <dump.xml> --fingerprint <fp>
  [--viewed-url ...] [--viewed-ad-id ...]`.
- 6 new tests (parser guards, storage linking, idempotency, REST, CLI).
- **OLX profile & settings management (`profile.py`)**: profile/settings
  screen parsers (name/phone/email/city/about, toggle states), kv mirror in
  storage (`olx_profile_kv`), guarded `ProfileEditor` — edits staged as
  `_pending_*` values, device only with `confirm=True`.
- **Competitor surveillance from own listings (`competitive.py`)**:
  `derive_query` from own titles, Jaccard+price+city link scoring,
  `olx_competitor_links` persistence, per-own undercut counts, price
  position (rank among similar ads).
- **Strategy advisor (`advisor.py`)**: per-own actions
  KEEP/EDIT_PRICE/EDIT_CONTENT/REPOST/PROMOTE with priorities and
  rationale; `advise_new_listings()` — active market queries the portfolio
  doesn't cover, with target price and seed title from market keywords.
- **Fresh-server bootstrap (`bootstrap.py` + `tools/olx_bootstrap.sh`)**:
  apt → Python deps → platform-tools → ADBKeyBoard → SDK cmdline-tools →
  Android 34 system image → headless AVD `aios-olx` → device setup, with
  dry-run plan by default and `doctor()` readiness checklist with fix hints.
- **REST**: `/olx/doctor`, `/olx/profile*` (parse/edit guarded),
  `/olx/competitive*`, `/olx/advisor` (with `?new=1`).
- **CLI**: `aios olx profile|profile-edit|competitive|advisor|bootstrap|
  doctor`.
- AutoWatch cycle now also reports competitive links and advisor actions.
- 17 new tests (`tests/test_olx_strategy.py` + REST additions).

## [9.0.0-alpha.3] - 2026-07-21

### Added
- **OLX search subscriptions & favorites (storage schema v4)**:
  - `SubscriptionManager`: named saved searches with price/city filters and
    new-ad alerts after each collection cycle (`olx_subscriptions`).
  - `FavoritesWatch`: favorite ads with price-drop alerts (`olx_favorites`).
  - Search deep-links with price-range and sorting filters
    (`OLXCollector.search_deep_link`).
- **AutoWatch (`autowatch.py`)**: one full unattended cycle — collect
  queries, match subscription alerts, favorite-drop alerts, own-ads snapshot,
  stagnant detection, improvement suggestions and repost plans, notifications.
- **`OwnAdEditor`**: applies improvement suggestions as a listing *edit*
  (keeps the ad id; DRY-RUN default, `confirm=True` to execute).
- **REST**: `/olx/subscriptions*`, `/olx/favorites*`, `/olx/own/edit`,
  `/olx/autowatch`.
- **CLI**: `aios olx subscribe|subscriptions|favorite|favorites|autowatch`.
- **Runbook**: `docs/modules/olx/DEVICE_RUNBOOK.md` — live-device setup
  (ADB, ADBKeyBoard for Cyrillic input, calibration, cron, Telegram alerts).
- **OLX ad detail parser (`detail.py`)**: full ad-page extraction — price,
  params, description, seller (name/type/since), city, views counter,
  publication date; resource-id and pure-text fallbacks.
- **OLX personal messenger (`messenger.py`)**: chat list and conversation
  parsers (direction via screen-side alignment), rule-based `ReplySuggester`
  (availability/bargain/meeting/greeting), and `OLXMessenger` with a guarded
  outbox — replies are enqueued and reach the device only via
  `auto_send=True` or an explicit flush.
- **Own listings control (`own_ads.py`)**: counters parser (views/favorites/
  messages/status), snapshot tracker with deltas and `stagnant()` detection
  (storage schema v3: `own_ads`, `own_ad_sightings`).
- **Improvement & guarded reposting (`promotion.py`)**: `AdImprover`,
  `RepostPlanner` (age/views-per-day + evening best-hours), `Reposter` —
  DRY-RUN by default with OLX duplicate-rules warning.
- **Notifications (`notifier.py`)**: webhook poster (Slack/Discord/Telegram)
  with price-drop and stagnant-listing alert helpers.
- **REST**: `/olx/detail`, `/olx/chats`, `/olx/chats/reply`, `/olx/outbox*`,
  `/olx/own*`, `/olx/notify`.
- **MCP tools** (read-only): `olx_market_stats`, `olx_listing_recommend`,
  `olx_price_drops`.
- **Dashboard OLX card** (`/api/olx` + UI block; `AIOS_OLX_DB` env).
- **CLI**: `aios olx detail|chats|reply|outbox|own|improve|repost`.
- 28 new tests (`tests/test_olx_actions.py` + REST additions).
- **OLX price history & activity tracking (storage schema v2)**:
  - `olx_sightings` table logs every observation (price/timestamp) per ad —
    full chronological price history via `OLXStorage.price_history()`.
  - `first_seen_at` / `last_seen_at` / `sightings_count` / `is_active`
    columns; v1 databases are migrated automatically.
  - `OLXStorage.sync_activity()` marks ads that vanished from the feed as
    inactive (typically sold), revives them when they reappear.
  - `PriceTracker`: `price_drops()` (first vs latest sighted price) and
    `gone_from_feed()` reports.
  - CSV/JSON export: `OLXStorage.export_csv()` / `export_json()`.
- **OLX REST endpoints**: `GET /api/v1/modules/olx/history` (per-ad price
  log) and `GET /api/v1/modules/olx/drops` (price drops + gone-from-feed).
- **CLI**: `aios olx collect|stats|recommend|export|history|drops`
  (`--db`, `--query`, `--format` options).
- Scheduler run records now include `deactivated` and `active` counters.

### Changed
- `AdCard.fingerprint` no longer includes the price: identity resolves via
  `ad_id` → `url` → `title|city|query`, so price edits are tracked as
  history of one ad instead of creating duplicate rows.
- `OLXCollector.collect_to_storage()` reports `deactivated` ads.

## [9.0.0-alpha.2] - 2026-07-21

### Added
- **OLX Collection Scheduler (`aios_core/modules/olx/scheduler.py`)**:
  - Thread-based periodic collection for a query list with run history
    (parsed/inserted/total counters per run), idempotent start/stop.
- **OLX REST endpoints (`/api/v1/modules/olx/*`)**:
  - `GET /ads` — stored ads with query filter and bounded limit.
  - `GET /stats` — competitor market statistics per query.
  - `POST /recommendations` — listing advice (price, verdict, keywords, TOP).
  - `POST /collect` — one-off ADB collection run.
  - `POST/DELETE /schedule` — start/stop periodic background collection
    (minimum interval guard).
  - Suites `tests/test_olx_api.py` and scheduler tests in
    `tests/test_olx_agent.py`.

### Changed
- `OLXStorage` is now thread-safe (`check_same_thread=False` + write lock) so
  it can be shared between the REST API and the scheduler thread.
- `AdCard.fingerprint` now includes the search query: the same ad found under
  different queries is tracked once per query, keeping per-query market
  reports consistent.

## [9.0.0-alpha] - 2026-07-21

### Added
- **OLX Parser Agent (`aios_core/modules/olx/`)** — completes the OLX Android Agent "next stage" plan:
  - `OLXCollector`: automated feed scrolling via ADB swipes with fingerprint deduplication and end-of-feed detection.
  - `CardParser` / `AdCard`: structured extraction of listing cards from UIAutomator dumps (title, price in UAH/USD/EUR, city, publication date for uk/ru locales, TOP badge, listing URL and ad id).
  - `OLXStorage`: deduplicating SQLite persistence for collected ads with query/city filters.
  - `CompetitorAnalyzer`: market statistics (min/max/mean/median price, TOP share, top cities, price percentile).
  - `RecommendationEngine`: suggested price (market median × 0.97), price verdict, title keywords and TOP-promotion advice.
  - Comprehensive unit test suite `tests/test_olx_agent.py` (589 total passed tests).

- **Android Play Store App-to-API Transformation Engine (`aios_core/android_rpa_bridge.py`)**:
  - Transforms Play Store App URLs (including OLX Ukraine `ua.olx.android`) into working programmatic REST APIs.
  - Automates UI emulator actions (search, view details, send direct messages, authentication) without manual screen clicking via endpoints (`/api/v1/apps/transform`, `/api/v1/apps/{package_name}/execute`).
  - Comprehensive unit test suite `tests/test_android_rpa_bridge.py` (572 total passed tests).

- **APK Function Converter & User API Profile Mapper (`aios_core/apk_converter.py`)**:
  - Converts Android APK exported components (Activities, Services, Receivers) into AIOS Capability instances, RBAC User API profiles, and API routes (`/api/v1/apk/convert`, `/api/v1/apk/profiles`).
  - Comprehensive unit test suite `tests/test_apk_converter.py` (570 total passed tests).

- **Milestone 9.0.3 Complete — Universal Multi-Species Ethics Framework (`aios_core/universal_multi_species_ethics.py`)**:
  - Multi-planetary ecological impact evaluation and biosphere non-disruption safety guarantees.
  - Comprehensive unit test suite `tests/test_universal_multi_species_ethics.py`.

- **Milestone 9.0.2 Complete — Bio-Digital Molecular DNA Runtime (`aios_core/molecular_dna_runtime.py`)**:
  - Translation of Constitutional Laws into synthetic DNA nucleotide sequences (A, T, C, G) with PCR molecule amplification simulation.
  - Comprehensive unit test suite `tests/test_molecular_dna_runtime.py`.

- **Milestone 9.0.1 Complete — Quantum Entangled Zero-Latency Communication Mesh (`aios_core/quantum_entanglement_mesh.py`)**:
  - Simulated EPR pair quantum teleportation channels with zero-latency state synchronization.
  - Comprehensive unit test suite `tests/test_quantum_entanglement_mesh.py` (567 total passed tests).

## [8.0.0-alpha] - 2026-07-21

### Added
- **Milestone 8.0.3 Complete — Cosmic Scale Swarm Matrix (`aios_core/cosmic_swarm_matrix.py`)**:
  - Light-speed delay vector compensation across inter-stellar nodes and holographic distributed memory shard state encoding.
  - Comprehensive unit test suite `tests/test_cosmic_swarm_matrix.py`.

- **Milestone 8.0.2 Complete — Self-Amending Infinite Constitutional Engine (`aios_core/infinite_constitution.py`)**:
  - Dynamic amendment synthesis with mathematical non-divergence alignment verification against core immutable axioms.
  - Comprehensive unit test suite `tests/test_infinite_constitution.py`.

- **Milestone 8.0.1 Complete — Universal Substrate-Agnostic Execution Engine (`aios_core/substrate_convergence.py`)**:
  - Substrate-agnostic task dispatching across Silicon, Photonic Optical, Neuromorphic SNN, Quantum QPU, and Bio-compute runtimes.
  - Comprehensive unit test suite `tests/test_substrate_convergence.py` (564 total passed tests).

## [7.0.0-alpha] - 2026-07-21

### Added
- **Milestone 7.0.3 Complete — Multi-Dimensional Universal World Model (`aios_core/multidimensional_world_model.py`)**:
  - Counterfactual predictive simulation engine forecasting system trajectories across CPU load, memory usage, economic cost, and system health.
  - Comprehensive unit test suite `tests/test_multidimensional_world_model.py`.

- **Milestone 7.0.2 Complete — Universal Constitutional Invariant Prover (`aios_core/universal_invariant_prover.py`)**:
  - Symbolic logic theorem prover evaluating state transition assertions against Constitutional invariants with SHA256 proof hashes.
  - Comprehensive unit test suite `tests/test_universal_invariant_prover.py`.

- **Milestone 7.0.1 Complete — Sovereign Recursive Self-Reflection Engine (`aios_core/sovereign_reflection.py`)**:
  - Metacognitive goal hierarchy auditor resolving belief contradictions and filtering malicious constitutional bypass attempts.
  - Comprehensive unit test suite `tests/test_sovereign_reflection.py` (561 total passed tests).

## [6.0.0-alpha] - 2026-07-21

### Added
- **Milestone 6.0.3 Complete — Planetary Mesh & Space Edge Orchestration (`aios_core/planetary_federation.py`)**:
  - Delay-Tolerant Network (DTN) mesh routing across terrestrial, orbital LEO satellites, and Lunar/deep space edge nodes.
  - Comprehensive unit test suite `tests/test_planetary_federation.py`.

- **Milestone 6.0.2 Complete — Autonomous Bio-Inspired Genetic Evolution Engine (`aios_core/biological_evolution.py`)**:
  - Chromosome genome encoding, single-point and uniform genetic crossover, Gaussian mutation, elitism survival selection, and constitutional integrity penalties.
  - Comprehensive unit test suite `tests/test_biological_evolution.py`.

- **Milestone 6.0.1 Complete — Neuromorphic Spiking Neural Network Matrix Engine (`aios_core/neuromorphic_matrix.py`)**:
  - Event-driven Leaky Integrate-and-Fire (LIF) spiking neuron arrays with membrane potential decay and spike firing reset.
  - Spike-Timing-Dependent Plasticity (STDP) unsupervised synaptic weight learning.
  - Comprehensive unit test suite `tests/test_neuromorphic_matrix.py` (558 total passed tests).

## [5.0.0-alpha] - 2026-07-21

### Added
- **Milestone 5.0.3 Complete — Quantum Native Computing & QAOA Engine (`aios_core/quantum_native.py`)**:
  - State vector Qubit simulator implementing Hadamard, CNOT, and measurement probabilities.
  - Quantum Approximate Optimization Algorithm (QAOA) solving NP-hard multi-agent task mapping graphs.
  - Comprehensive unit test suite `tests/test_quantum_native.py`.

- **Milestone 5.0.2 Complete — Global Swarm Governance & ZK Safety Proofs (`aios_core/global_swarm.py`)**:
  - W3C DID Node Identity protocol (`did:aios:<node_id>`) for inter-cluster federation.
  - Zero-Knowledge Safety Proofs (`ZeroKnowledgeSafetyProof`) ensuring zero-trust cross-cluster task verification without exposing secret task variables.
  - Byzantine Fault Tolerant (BFT) and Bayesian consensus voting engine for constitutional amendment proposals.
  - Comprehensive unit test suite `tests/test_global_swarm.py`.

- **Milestone 5.0.1 Complete — Real-Time Formal Code Verification Engine (`aios_core/formal_code_verifier.py`)**:
  - Abstract Syntax Tree (AST) AST-level static invariant proofs, infinite loop detection, reflection and dunder exploit blocking (`__subclasses__`, `__globals__`).
  - Pre/post-condition mathematical contract checking and import whitelist enforcement.
  - Comprehensive unit test suite `tests/test_formal_code_verifier.py` (549 total passed tests).

## [4.2.0-alpha] - 2026-07-21

### Added
- **Milestone 4.2.4 Complete — Enterprise Scaling & PostgreSQL Integration**:
  - Multi-dialect `Database` abstraction (`aios_core/storage.py`) handling transparent query translation between SQLite and PostgreSQL.
  - Kubernetes HorizontalPodAutoscaler template (`helm/aios/templates/hpa.yaml`) scaling based on target CPU/Memory metrics and task queue depth.
  - Comprehensive unit test suite `tests/test_storage_postgresql.py` (543 total passed tests).

- **Milestone 4.2.3 Complete — Official Web UI (React + TypeScript + Tailwind SPA)**:
  - Enterprise React SPA interface with tabbed views: Overview, Safety Dashboard, Agent Swarm Topology, Master Constitution (67 Articles), Knowledge Graph, and ML Model Registry.
  - Dedicated REST API endpoints in `aios_core/api/app.py`: `/api/v1/constitution`, `/api/v1/safety`, `/api/v1/knowledge-graph`, `/api/v1/agents`, `/api/v1/models`.
  - Comprehensive unit test suite `tests/test_web_ui_integration.py` (540 total passed tests).

- **Milestone 4.2.2 Complete — Production Hardening & Observability**:
  - `Telemetry` & OpenTelemetry metrics (`aios_core/telemetry.py`) with counters, gauges, histograms, and Prometheus exposition formatting.
  - `Tracer` W3C Trace Context propagation (`aios_core/tracing.py`) supporting `traceparent` (`00-{trace_id}-{span_id}-01`) headers, sub-spans, and thread-local context propagation.
  - `JSONFormatter` (`aios_core/logging_config.py`) for structured production logs enriched with `trace_id`, `span_id`, `agent_id`, and `constitutional_status`.
  - `BackupManager` (`aios_core/backup_manager.py`) with zero-downtime hot online SQLite snapshotting (`sqlite3.backup` API), SHA256 integrity validation, and retention policy cleaning.
  - Comprehensive unit test suites `tests/test_telemetry.py` and `tests/test_backup_manager.py` (535 total passed tests).

- **Milestone 4.2.1 Complete — Advanced ML Intelligence Layer**:
  - `ModelRegistry` (`aios_core/model_registry.py`) with artifact SHA256 hashing, stage promotion (`staging`, `production`), weight versioning, and evaluation metric logging.
  - `ModelServer` (`aios_core/model_serving.py`) with A/B traffic splitting, thread-safe inference, batch predictions, and latency tracking.
  - `AnomalyDetector` (`aios_core/anomaly_detection.py`) with Z-score and IQR statistical outlier detection for runtime metrics.
  - `PredictiveAutonomyRegulator` (`aios_core/predictive_autonomy.py`) dynamically risk-scoring agent plans and downgrading autonomy levels upon critical risk.
  - Comprehensive unit test suite `tests/test_ml_registry.py` (530 total passed tests).

## [4.1.0-alpha] - 2026-07-21

### Added
- **Constitutional Verification Tool (`tula`)** — autonomous tool (`tools/complete_constitution_tula.py`) for scanning articles I-LXVII, strict structure verification, compliance matrix generation, master index tracking, and report generation.
- **AI Safety & Ethics Test Suite** — comprehensive unit tests for safety layers, real-time safety monitor, dashboard, ethics evaluator, and benchmarks (`tests/test_ai_safety_framework.py`).
- **Cognition & Role Engine Test Suite** — unit tests for Theory of Mind, Emotional Intelligence, Metacognition, Social Intelligence, Creativity, AI Scientist, AI Researcher, AI Engineer, AI Product Manager, AI Startup (`tests/test_cognition_framework.py`).
- **Constitutional Verification Test Suite** — automated test suite for `tula` (`tests/test_tula.py`).
- Total test coverage expanded to **526 passed tests** (100% passing).

### Changed
- Unified versioning across `aios_core/__init__.py`, REST API `/health`, and tests to `4.1.0-alpha`.
- Fixed typing and compilation constraints in `ai_safety_evals.py` and `ai_safety_benchmark.py`.
- Updated `docs/constitution/COMPLIANCE_MATRIX.md`, `docs/constitution/INDEX.md`, and `docs/constitution/CONSTITUTION_REPORT.md` with full 67-article mapping.

## [4.0.0-alpha] - 2026-07-21

### Added
- **FederationManager** — multi-node coordination, task delegation, broadcast
- **MLPlannerScorer** — ML-enhanced plan scoring and optimization
- **MultiAgentOrchestrator** — dynamic team formation and conflict resolution
- **ConstitutionEvolver** — self-evolving constitution with automatic proposals
- **Web Dashboard** — real-time monitoring interface (Starlette)
- Full integration of all v4.0 subsystems into `Orchestrator`
- 20+ new tests for v4.0 components (total: 501 passing)

### Changed
- `Orchestrator.stats()` now includes `federation`, `ml_scorer`, `multi_agent`, `constitution_evolver`
- Enhanced autonomy with automatic level adjustment
- Improved monitoring (`/metrics`, `monitor.py`)

### Infrastructure
- Docker + docker-compose support
- Prometheus-compatible metrics
- Production-ready deployment files

## [3.1.0] - 2026-07-21

### Added
- Enhanced monitoring and health endpoints
- Docker support
- 485+ tests

## [3.0.0] - 2026-07-19

Initial stable release with full constitution (67 articles), orchestrator, evolution, and API layers.

---

**Next milestone:** v4.1 (Kubernetes operator, official SDK, capability marketplace)
