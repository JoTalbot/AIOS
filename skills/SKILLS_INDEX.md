# SKILLS INDEX — каталог скиллов Octopus
*Сгенерировано: 2026-07-13T18:53:03+00:00 · всего 242 скиллов*

Физические top-level категории соответствуют папкам в `skills/`. Описание — первая содержательная строка SKILL.md.

## Сводка по категориям

- **core/** — 132
- **memory/** — 32
- **swarm/** — 34
- **meta/** — 36
- **mcp/** — 2
- **research/** — 4
- **dr/** — 2

---

## core/ (132)

- **`agent-recovery-grant-guard`** — Проверяет безопасную выдачу одноразового SSH grant через Telegram approval.
- **`ai-skill-improver`** — Анализирует скиллы и генерирует bounded AI-предложения по их улучшению.
- **`all-vectors-orchestrator`** — Навык безопасно собирает состояние всех стратегических векторов Octopus, формирует score/roadmap и з
- **`amendment-applier`** — Применяет согласованные правки (amendments) к инструкциям и конфигам с откатом.
- **`api-contract-checker`** — Проверяет соответствие API контрактам: endpoints, схемы запросов/ответов, HTTP-статусы.
- **`api-rate-limit-audit`** — Аудит rate-limit настроек на публичных API endpoints Octopus.
- **`api-smoke-matrix`** — Прогоняет матрицу smoke-тестов по всем API endpoints и фиксирует результат.
- **`arch-lens`** — 1. Explore codebase for shallow modules / hidden coupling
- **`audio-pipeline-latency`** — Измеряет задержку аудио-пайплайна (Whisper/VAD/transcribe) на ноде.
- **`audio-transcribe-workflow`** — 1. VAD silero on chunk 180s
- **`autopilot-runtime-durability-guard`** — Prevents the public Octopus autopilot API from silently running as an unmanaged orphan with missing
- **`backup-gap-analyzer`** — Выявляет пробелы в графике и покрытии бэкапов системы.
- **`capability-registry`** — Для каждой ноды:
- **`chaos-monkey-lite`** — Bounded-внедрение контролируемых сбоев для проверки устойчивости сервисов.
- **`chaos-readiness-plan`** — Оценивает готовность системы к chaos-тестированию и формирует план.
- **`chaos-test-guard`** — 1. Simulate node failures (bounded)
- **`config-drift-audit`** — Обнаруживает расхождения (drift) между конфигами и каноническим состоянием.
- **`consent-gate-enforcer`** — Проверяет, что все gated-действия имеют открытое human consent (#18).
- **`context-fundamentals`** — 1. Informativity over exhaustiveness
- **`cost-anomaly-reader`** — Выявляет аномальные расходы и usage в облачных аккаунтах (read-only).
- **`creative-evolution`** — Auto-generates evolutionary summaries from system data, experience, and metrics.
- **`cron-safety-audit`** — Проверяет cron/systemd-timer правила на безопасность, конфликты и риски.
- **`dashboard-ux-review`** — Аудит UX и доступности веб-дашбордов Octopus.
- **`data-quality-sampler`** — Сэмплирует и оценивает качество данных в хранилищах памяти.
- **`dead-code-hunter`** — Обнаруживает мёртвый и недостижимый код в проекте Octopus.
- **`deep-cleanup`** — 1. Загрузить `SKILL.md`, контекст проекта Octopus и последние отчёты по направлению навыка.
- **`dependency-risk-audit`** — Проверяет зависимости на известные уязвимости и устаревшие версии.
- **`development-mode`** — "development mode on"
- **`disk-growth-forecast`** — Прогнозирует заполнение диска по историческим данным использования.
- **`disk-space-monitor`** — Мониторит свободное место на дисках нод роя.
- **`documentation-sync`** — Проверяет синхронизацию документации с фактическим кодом и конфигами.
- **`dr-config-preflight`** — Единый bounded preflight и schema/introspection слой для DR/bootstrap/snapshot/memory scripts.
- **`dynamic-policy-applier`** — 1. Загружает активные политики из policy-engine
- **`dynamic-tool-orchestrator`** — Динамически управлять набором запущенных скриптов, сервисов, моделей и функционала на каждой ноде (и
- **`eternal-bootstrap`** — 1. Run eternal-snapshot.py
- **`eternal-drill`** — 1. Run /opt/octopus-eternal-snapshot.py
- **`eternal-merkle-guard`** — 1. Build Merkle for pack + manifests
- **`experience-analyst`** — Анализирует опыт и логи прошлых итераций, извлекает уроки (#06).
- **`github-actions-health-reader`** — Проверяет состояние и последние запуски GitHub Actions workflows.
- **`global-coordination-hub`** — 1. Aggregate node status across federation
- **`graphrag-exact-citations`** — Read-only GraphRAG search API returning auditable provenance for every result: exact source path, in
- **`incident-postmortem-writer`** — Формирует postmortem-отчёт по инциденту на основе логов и метрик.
- **`incident-triage`** — Первичная классификация и приоритизация инцидентов.
- **`integration-testing`** — Comprehensive integration test suite for all Octopus components.
- **`llm-evaluation-lite`** — Bounded оценка качества LLM-ответов без отправки данных наружу (read-only).
- **`load-aware-scheduler`** — - Текущая загрузка CPU/RAM/GPU на нодах
- **`log-retention-audit`** — Проверяет политику удержания и ротации логов на соответствие гигиене.
- **`log-summarizer`** — Суммаризирует объёмные логи в краткий отчёт с ключевыми событиями.
- **`market-rate-calculator`** — Расчёт рыночных курсов и ставок для вектора самообеспечения (#46).
- **`metrics-correlator`** — Коррелирует метрики для поиска причинно-следственных связей между событиями.
- **`mode-manager`** — - development (то, что просил пользователь)
- **`model-router`** — Маршрутизирует LLM-запросы между моделями (Ollama/external) по заданным правилам.
- **`money-earner-orchestrator`** — Навык-оркестратор вектора САМООБЕСПЕЧЕНИЕ: catalogue, probe и bounded-развитие всех
- **`network-latency-monitor`** — Измеряет сетевую задержку между нодами роя.
- **`nginx-route-auditor`** — Аудит nginx-маршрутов, прокси-конфигов и location-правил.
- **`obsidian-export-quality`** — Проверяет качество Obsidian-экспорта заметок из памяти Octopus.
- **`octopus-agentmem-vectorizer`** — Векторизует заметки и объекты памяти для RAG-поиска.
- **`octopus-ai-rewriter`** — Bounded AI-переписывание текста и кода по заданным правилам и лимитам.
- **`octopus-alert-thresholds`** — Octopus threshold alerts: deduplicated, no secrets, always exit 0.
- **`octopus-alerting`** — Octopus Alerting Daemon v2 (2026-05-18).
- **`octopus-alerts-tg`** — Octopus Prometheus Alerts → Telegram bridge (2026-05-18).
- **`octopus-anomaly-detect`** — Выявляет аномалии в метриках и событиях системы Octopus.
- **`octopus-audio-backup`** — Бэкап аудиофайлов в децентрализованное хранилище (IPFS).
- **`octopus-audio-daily-digest`** — Ежедневный дайджест аудио-событий и транскрипций.
- **`octopus-audio-sync`** — INSERT INTO octopus_image_vectors (ref, source, embedding, metadata)
- **`octopus-auto-deploy`** — Bounded авто-деплой сервисов и обновлений на ноды.
- **`octopus-autoheal`** — Самомониторинг и автоматическое восстановление упавших сервисов.
- **`octopus-autoheal-corruption`** — Обнаружение повреждения данных и восстановление после него.
- **`octopus-autolink`** — Автоматическая простановка связей между сущностями в графе знаний.
- **`octopus-autonomy-journal`** — Журнал автономных решений системы для подотчётности человеку (#18).
- **`octopus-autoscale-local`** — Guarded local autoscaler for Octopus child nodes.
- **`octopus-cas-api`** — Octopus unified CAS API (read-only).
- **`octopus-clip-api`** — API для работы с клипами и фрагментами медиаданных.
- **`octopus-coexistence-guard`** — 1. Check human_consent.env + cgroups
- **`octopus-crypto-verify`** — Crypto-верификация целостности памяти (v2): packs + loose + pack-read sample.
- **`octopus-db-cleanup`** — Периодическая очистка устаревших offline нод из PostgreSQL.
- **`octopus-dev-agent`** — Агент разработки: кодогенерация и bounded-правки по задаче.
- **`octopus-disk-monitor`** — Непрерывный мониторинг дискового пространства нод.
- **`octopus-dr-drill`** — Octopus Disaster-Recovery Drill (vector #8 ПАМЯТЬ).
- **`octopus-dynamic-tools`** — octopus-dynamic-tools — Phase D5 prep: policies + load-aware scheduler.
- **`octopus-env-validate`** — Валидация переменных окружения и конфигурационных файлов.
- **`octopus-eternal-snapshot`** — Создание eternal-снимка системы для Disaster Recovery (#19).
- **`octopus-events-api`** — Unified events API — serves event log as JSON.
- **`octopus-garage-health`** — Small, no-secret Garage health probe for Octopus alerts/dashboards.
- **`octopus-garage-preflight`** — Preflight-проверка Garage (S3-совместимого хранилища) перед операциями.
- **`octopus-guardian`** — Общий guardian: проверка системных инвариантов и safety-условий.
- **`octopus-http-replicator`** — SELECT ref, key, mime_type, size_bytes, is_encrypted, is_signed, is_worm,
- **`octopus-image-search`** — SELECT ref, metadata, 1 - (embedding <=> %s::vector) AS score
- **`octopus-image-sync`** — INSERT INTO octopus_image_vectors (ref, source, embedding, metadata)
- **`octopus-multisync`** — Multi-master Active-Active синхронизация данных между нодами (#19).
- **`octopus-node-exporter`** — Octopus Node Status Exporter (2026-05-18).
- **`octopus-obsidian-export`** — 1. Read CAS objects or memory_pool
- **`octopus-rag-indexer`** — Индексация данных и документов для RAG-поиска по памяти.
- **`octopus-rag-search`** — Real embedding via Ollama nomic-embed-text (dim=768, matches octopus_vectors HNSW).
- **`octopus-status-page`** — Публичный статус-экран роя Octopus. Порт 8080.
- **`octopus-vector-search`** — Standalone vector search service for Octopus Memory.
- **`octopus-voice-rag`** — 1. Transcribe (whisper + VAD)
- **`orphan-dependency-checker`** — Обнаружение неиспользуемых и осиротевших зависимостей в проекте.
- **`orphan-session-drift-guard`** — Read-only detection of abandoned systemd sessions containing strongly classified stale or runaway PP
- **`people-graph-octopus`** — 1. ECAPA 0.75 speaker ID from whisper
- **`people-graph-quality`** — Проверка качества графа людей (speaker ID, связность).
- **`persistent-terminal-manager`** — Этот скилл позволяет создавать и управлять долгоживущими сессиями терминала (PTY). В отличие от обыч
- **`proactive-self-modification`** — Proactive anomaly detection and self-modification system. Integrates with the Load Forecaster and Re
- **`prompt-regression-checker`** — Проверяет регрессии в LLM-промптах между версиями.
- **`rag-hybrid`** — 1. Semantic vector (pgvector)
- **`rag-index-drift`** — Обнаруживает расхождения (drift) между RAG-индексом и исходными данными.
- **`railway-health-reader`** — Проверяет здоровье и статус Railway-сервисов Octopus.
- **`ram-usage-monitor`** — Мониторинг использования RAM на нодах роя.
- **`resource-aware-scheduler`** — Планировщик задач с учётом загрузки ресурсов нод.
- **`resource-demand-evaluator`** — - Текущий "режим" проекта (development / production / maintenance / testing)
- **`resource-optimizer`** — Предлагает оптимизации использования CPU/RAM/диска.
- **`review-api-design`** — 1. Review domains (security, resilience, design, ops)
- **`roadmap-slicer`** — Нарезает roadmap на bounded-шаги для исполнения автономным агентом.
- **`rollback-catalog-maintainer`** — Ведёт каталог rollback-команд для всех изменений.
- **`rollback-readiness`** — Проверяет готовность системы к безопасному откату изменений.
- **`script-deployer`** — - deploy(tool_name, version, target_nodes)
- **`secrets-hygiene-audit`** — Аудит гигиены секретов: поиск plaintext-кредов в конфигах/логах (#51).
- **`security-port-guard`** — Мониторинг открытых портов и предотвращение появления несанкционированных прослушивателей.
- **`self-bootstrapper-v3`** — Самозагрузка Octopus на новой ноде из eternal-снимка.
- **`self-healing-swarm`** — 1. Monitor health.json, packguard, skills loader
- **`self-test-generator`** — Генерирует тесты для скиллов и компонентов автоматически.
- **`service-dependency-map`** — Строит карту зависимостей между сервисами Octopus.
- **`smoke-scenario-runner`** — Прогоняет smoke-сценарии ключевых пользовательских потоков.
- **`software-reporter`** — Отчёт об установленном ПО, версиях и обновлениях на ноде.
- **`systemd-unit-lint`** — Lint systemd-unit файлов на ошибки и лучшие практики.
- **`task-prioritizer`** — Приоритизирует задачи по векторам развития и срочности.
- **`telegram-noise-auditor`** — Аудит Telegram-шума: поиск несанкционированных отправителей (#28).
- **`tool-desired-state`** — Каждая нода и весь кластер имеют **Desired State** — что должно быть запущено/установлено.
- **`tunnel-health-audit`** — Проверка здоровья SSH и Cloudflare-туннелей между нодами.
- **`unused-resource-reclaimer`** — Scans system for unused resources and reports them safely.
- **`vault-scribe`** — 1. Read input (transcript / JSON / CAS object)
- **`web-research`** — Performs autonomous web research using the Browser Vision MCP server (port 8909).

## memory/ (32)

- **`archive-rotation-reader`** — Аудит ротации архивов памяти: устаревшие, потерянные, невосстановимые.
- **`archived-report-resurrection-reconciler`** — После verified compaction удалённые ITER-файлы могут повторно появиться из-за legacy multisync, кото
- **`cas-credential-boundary-guard`** — Fail-closed drift guard for CAS credential storage and authentication. It never prints token values.
- **`cas-integrity-reader`** — Read-only проверка целостности CAS-объектов (sha256, pack-читаемость).
- **`cas-pack-guard`** — Use on any CAS write, pack read, eternal-drill, multisync.
- **`cas-replication-guard`** — 1. Check pack_index + zstd.dict + SHA
- **`dna-shard-audit`** — Validates integrity of DNA shards across the swarm. Checks SHA256 of each shard
- **`dna-sharding-guard`** — Erasure coding for Octopus memory DNA. Splits CAS/packstore data into 5 shards
- **`immortal-memory-orchestrator`** — 1. Ensure N independent copies
- **`ipfs-pin-audit`** — Аудит IPFS-pin'ов: что запиннено, что открепилось, что потеряно.
- **`memory-immortal-guard`** — 1. Check pack_read_guard + off-host copies
- **`memory-ipfs-exporter`** — Экспорт объектов памяти в децентрализованное хранилище IPFS.
- **`memory-merkle-guard`** — Проверка Merkle-хэшей целостности памяти по backends.
- **`memory-retrieval-quality`** — Оценка качества извлечения из памяти (RAG recall/precision).
- **`memory-systems`** — - Working: context
- **`merkle-auto-monitor`** — Автоматический ежечасный мониторинг целостности памяти через Merkle Master Hash.
- **`octopus-archive-rotate`** — Ротация и устаревание архивов памяти по политике retention.
- **`octopus-ipfs-pin-coordinator`** — SELECT ref, attrs FROM memory_records
- **`octopus-memory-copies-audit`** — Octopus memory invariant audit: every local memory object MUST have at least
- **`octopus-memory-coverage-alert`** — Octopus: alert if memory_copies_audit.json shows coverage < 1.0 or stale.
- **`octopus-memory-dashboard`** — Memory Dashboard — simple HTTP dashboard for memory stats.
- **`octopus-memory-drill-api`** — API для запуска restore-дриллов памяти (учебных восстановлений).
- **`octopus-memory-exporter`** — Prometheus exporter for Octopus memory metrics.
- **`octopus-memory-gc-dryrun`** — SELECT ref,key,size_bytes,is_worm,replication_count,COALESCE(tags,'[]'::jsonb),COALESCE(attrs,'{}'::
- **`octopus-memory-indexer`** — Octopus Memory Indexer.
- **`octopus-memory-manifest`** — Octopus: ежедневный manifest sha256 для каждого backend.
- **`octopus-memory-replicator`** — UPDATE memory_records mr
- **`octopus-memory-restore-alert`** — Алерт при сбое restore-операции памяти.
- **`octopus-memory-restore-drill`** — Учебный restore-дрилл: проверка восстанавливаемости памяти.
- **`octopus-memory-restore-drill-ec2`** — Octopus: restore-drill для AWS EC2-ноды (через SSH+sha256sum).
- **`octopus-pack-read-guard`** — Pack-Read Guard: проверяет, что packed-объекты реально читаются из pack
- **`strict-iter-archive-gate`** — Создаёт проверенные tar.gz архивы и `ITER_FILES_ARCHIVED.md` markers для завершённых unmarked `paral

## swarm/ (34)

- **`auto-reproduction`** — 1. Загрузить `SKILL.md`, контекст проекта Octopus и последние отчёты по направлению навыка.
- **`barter-policy-enforcer`** — Enforcement правил resource-barter между нодами роя.
- **`bft-consensus`** — 1. Загрузить `SKILL.md`, контекст проекта Octopus и последние отчёты по направлению навыка.
- **`bft-lite`** — 1. Threshold signatures for critical decisions
- **`bft-lite-validator`** — Валидатор BFT-lite консенсусных сообщений от нод.
- **`consensus-heartbeat`** — Heartbeat для консенсус-протокола роя: liveness-проверка.
- **`cross-swarm-voting`** — Голосование между разными swarm'ами для федеративных решений.
- **`docker-child-capacity`** — Проверка capacity для развёртывания docker child-нод.
- **`federated-event-bus`** — Федеративная шина событий между нодами роя.
- **`free-tier-preflight`** — Preflight перед использованием free-tier ресурсов (#09).
- **`geo-aware-routing`** — Optimizes swarm traffic based on geographic location and latency.
- **`geo-latency-resolver`** — Resolver географической задержки для оптимальной маршрутизации.
- **`inter-swarm-collab`** — 1. Загрузить `SKILL.md`, контекст проекта Octopus и последние отчёты по направлению навыка.
- **`node-capability-advertiser`** — 1. Собрать:
- **`node-health-orchestrator`** — 1. Aggregate health.json from all nodes
- **`node-reputation`** — Tracks node reliability, uptime, and contribution to swarm.
- **`node-reputation-reader`** — Read-only чтение репутации нод роя из реестра.
- **`p2p-federation`** — 1. Nostr event publishing for skills/market
- **`reproduction-guard`** — 1. Check human_consent.env
- **`resource-barter`** — Nodes trade resources (CPU, memory, storage, bandwidth) using reputation-based tokens.
- **`resource-coexistence`** — Проверка соблюдения лимитов сосуществования (CPU/RAM) на ноде (#18).
- **`self-replication-validator`** — Валидация безопасности и необходимости self-replication шагов.
- **`swarm-coordination`** — 1. Bootstrap KAD
- **`swarm-discovery`** — P2P handshake protocol for discovering and registering swarm nodes.
- **`swarm-discovery-protocol`** — Протокол обнаружения и регистрации нод в P2P-сети роя.
- **`swarm-health-guard`** — 1. Check /run/octopus/health.json, slo_status
- **`swarm-load-forecaster`** — Predictive load analysis for the Octopus swarm. Collects real system metrics (CPU load, memory, disk
- **`swarm-reasoning`** — 1. Загрузить `SKILL.md`, контекст проекта Octopus и последние отчёты по направлению навыка.
- **`swarm-reasoning-hub`** — Хаб коллективного рассуждения роя: агрегация выводов нод.
- **`swarm-reproduction`** — 1. Eternal snapshot + bootstrap
- **`swarm-resource-barter`** — Обмен ресурсами (CPU/storage/bandwidth) между нодами роя.
- **`swarm-version-checker`** — Проверка версий ПО и кода на нодах роя (consistency).
- **`swarm-voting`** — Cross-swarm voting with reputation-weighted consensus.
- **`vote-weight-calculator`** — Расчёт весов голосов нод (reputation-weighted consensus).

## meta/ (36)

- **`auto-documentation-summarizer`** — ```markdown
- **`barter-ledger`** — Ledger транзакций resource-barter: история обмена ресурсами.
- **`consent-orchestrator`** — 1. Read human_consent.env + chat approvals
- **`cost-free-orchestrator`** — 1. Monitor all free resources (Oracle, Fly, Pi, GitHub)
- **`development-mode-guard`** — "Включи development mode"
- **`dynamic-capability-sync`** — - Периодически синхронизировать capability-registry между нодами
- **`federated-marketplace`** — 1. Pull/push via Nostr/Matrix
- **`free-tier-orchestrator`** — 1. Inventory of free resources
- **`mcp-server-expose`** — 1. skills/list + skills/get via MCP
- **`octopus-full-mcp-guard`** — 1. Verify MCP daemon (PID, logs, health)
- **`parallel-replicator`** — Параллельная репликация данных между нодами для скорости.
- **`policy-engine`** — - Правила в YAML/JSON
- **`priority-sync-manager`** — Менеджер приоритетной синхронизации критичных данных.
- **`proactive-scaling`** — Проактивное масштабирование ресурсов на основе прогноза нагрузки.
- **`reputation-engine`** — Движок расчёта репутации нод по uptime, вкладу и надёжности.
- **`skill-archive-cleaner`** — Очистка и архивация устаревших скиллов по политике.
- **`skill-auto-update`** — Автообновление скиллов по schedule (AI-proposals, structural repair).
- **`skill-autonomous-agent`** — Автономный ИИ-агент, который постоянно работает над развитием проекта Octopus
- **`skill-coverage-audit`** — Аудит покрытия скиллов: пробелы, дубли, заглушки (#31).
- **`skill-creator`** — 1. Interview for use-case
- **`skill-factory`** — 1. Загрузить `SKILL.md`, контекст проекта Octopus и последние отчёты по направлению навыка.
- **`skill-factory-ai`** — AI-генерация новых скиллов из опыта и задач системы.
- **`skill-health-monitor`** — Автоматический мониторинг здоровья всех компонентов системы Octopus.
- **`skill-integrity-check`** — Проверка целостности скиллов: структура, тесты, код-валидность.
- **`skill-marketplace-sync`** — 1. Pull latest from index
- **`skill-notification`** — Отправляет уведомления человеку через Telegram бот (YakForumsBot) и записывает в журнал автономии.
- **`skill-registry-sync`** — 1. Build compact registry from all SKILL.md
- **`skill-rollback`** — Откат изменений в скиллах к предыдущей рабочей версии.
- **`skill-schedule-runner`** — Выполняет запланированные задачи по расписанию. Поддерживает интервалы и фиксированное время.
- **`skill-task-decompose`** — Декомпозирует задачу на подзадачи, распределяет по векторам развития (#05, #11),
- **`skill-telegram-control-panel`** — Скилл формализует Telegram как основной человеко-ориентированный интерфейс управления Octopus.
- **`skill-version-manager`** — Управление версиями скиллов: bump, tag, changelog.
- **`skill-web-dashboard`** — Простой HTTP сервер, отдающий HTML-дашборд с текущим состоянием проекта Octopus.
- **`third-party-node-guard`** — 1. Health + SLO checks
- **`universal-loader-health`** — 1. Compare metadata vs files
- **`universal-skill-loader-guard`** — Use when loader health is questioned, after adding new skills, or during marketplace sync.

## mcp/ (2)

- **`browser-vision`** — Local browser automation and visual control server at `http://127.0.0.1:8897`.
- **`telegram-control`** — Use local server `http://127.0.0.1:8898` for Telegram Bot API operations and gated personal-account

## research/ (4)

- **`global-symbiotic-search`** — Глобальный поиск по партнёрским и симбиотическим данным.
- **`knowledge-linker`** — Связывание разрозненных знаний в единый граф.
- **`partner-memory-indexer`** — Индексация памяти партнёров для кросс-проектного поиска.
- **`symbiotic-query`** — Запросы к симбиотической памяти роя нод.

## dr/ (2)

- **`arweave-dna-mirror`** — Зеркало DNA-данных в Arweave для permanent storage (DR).
- **`nodes-restore-nostr`** — Восстановление списка и состояния нод через Nostr-протокол.
