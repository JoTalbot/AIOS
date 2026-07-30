# Octopus — Deep Research Roadmap / параллельные векторы развития
Дата: 2026-06-20 UTC
Итерация: Arena repair + research + roadmap

## 0. Текущая стабилизация, выполненная перед планированием
- Прочитаны общие инструкции `~/agents/` и контекст проекта `~/agents/-Octopus/`.
- Проведён bounded-аудит: `octopus health`, `octopus test`, systemd failed/autorestart, NRestarts, порты, Docker/Swarm, Railway health, disk.
- Найдена причина restart-loop parent: `octopus-watchdog.py` перезапускал `octopus.service` через SSH для registry-нод `127.0.0.1` (home/ubu tunnel children), потому что `/api/v1/node/info` возвращал 404. Исправлено: для localhost/tunnel нод TCP-open считается OK, SSH restart parent запрещён.
- Исправлен ложный `auto-restart` у `octopus-ipfs-subscriber.service`: сервис фактически bounded 30s publish/listen, переведён в `Type=oneshot`, `Restart=no`.
- Исправлен потенциально зависающий `octopus-swarm-discovery.service`: добавлен bounded timeout (`timeout 150`, `TimeoutStartSec=180`).
- Удалён конфликтующий legacy `octopus-prometheus` container, который рестартовал из-за порта 9090 при наличии Swarm Prometheus.
- Проведена безопасная очистка: apt cache, journal vacuum, удаление pycache, hardlink-dedupe крупных одинаковых файлов/pack copies. Disk: 94% → 90%.
- Финальная проверка: `octopus test` = 16/16 pass, NRestarts=0, core services active.

## 1. Исследовательская база

### 1.1 GitHub/repository sweep
Файл: `/root/agents/-Octopus/research/2026-06-20_15-56-05_github_50_queries.md`
- Выполнено 50 вариаций repository search по векторам: swarm, P2P, CRDT, RAG, Temporal, Ray, LangGraph/CrewAI/AutoGen, MCP, OTel, BFT/Raft, IPFS/Garage/MinIO, backup, vector DB, audio RAG, Ollama/vLLM/SGLang, autoscaling, NATS/Redpanda/Celery.
- 29 запросов успешно вернули GitHub API результаты, 21 упёрся в API 403/rate-limit; сами query-вариации и partial results сохранены для последующего дозапуска с токеном/паузацией.

### 1.2 Web/current research synthesis
Ключевые выводы из web research:
- Agent stack 2026 фрагментирован; устойчивые слои: serving (Ollama/vLLM/SGLang), framework (LangGraph/CrewAI/AutoGen/Pydantic AI), memory/RAG, MCP tools, trace/eval поверх OpenTelemetry/OpenInference.
- Durable execution для агентов становится отдельным слоем: Temporal подходит для задач, которые должны переживать crash/restart, human-in-loop и длинные workflows.
- Ray подходит не для control-plane, а для burst/ML/embedding/audio batch compute на ubu-worker или будущих GPU/free nodes.
- KEDA полезна при переходе на Kubernetes/event-driven autoscaling; для текущего Docker Swarm нужна облегчённая альтернатива: forecast → desired replicas → bounded actuator.
- IPFS + CRDT-подход остаётся релевантным для distributed shared state, но GC разрешён только после live-read checks и off-host copies.

## 2. Главный принцип roadmap
Безопасность и суверенитет человека выше размножения. Новые внешние ресурсы — только после явного подтверждения. Параллелизм — через независимые bounded-потоки с backup → change → verify → log.

## 3. Независимые потоки развития

### Stream A — Reliability / SLO / restart-loop immunity (P0)
Цель: больше не допустить self-inflicted restarts.
1. Добавить `localhost/tunnel` policy в Node Registry schema: `check_type=tcp_only`, `restart_strategy=none|local_container|ssh_remote`.
2. Watchdog: restart target должен быть явным полем, не hardcoded `octopus.service`.
3. Добавить тест `watchdog_does_not_restart_parent_for_127001`.
4. Health endpoint contract: parent `:8000` должен отдавать `/healthz` 200 или health checker должен использовать существующий endpoint.
5. Ввести restart budget: max 1 restart/15min/service, дальше quarantine + alert.

### Stream B — Disk / storage discipline (P0)
Цель: 90% → 75% без потери памяти.
1. Garage audit: buckets, object age, duplicate backup prefixes; только read-only inventory сначала.
2. Containerd/Docker audit: какие images реально нужны Swarm/legacy; удалить только stopped/obsolete.
3. Packstore: оставить hardlink-dedupe, но добавить read-guard после dedupe.
4. Перенести тяжёлые ML venv/models на ubu-worker; parent оставить control-plane.
5. Автоматический disk budget: alert 80%, freeze noncritical writes 85%, cleanup plan 90%.

### Stream C — Durable orchestration / Temporal-lite (P1)
Цель: заменить ad-hoc cron/timers для длинных задач на durable workflows.
1. MVP без нового сервера: локальный Temporal dev/Postgres или lightweight queue journal.
2. Первые workflows: research sweep, backup+verify, pack-read-guard, audio batch, roadmap execution.
3. Human approval gates как workflow signals.
4. Метрики workflow duration/failures в Prometheus.

### Stream D — Agent framework / MCP tools (P1)
Цель: унифицировать инструменты агентов.
1. MCP server для Octopus ops: status, test, logs, registry read, safe cleanup proposal.
2. LangGraph/Pydantic AI pilot для bounded planning; не заменять core сразу.
3. Tool sandbox: read-only по умолчанию; write requires consent gate.
4. Trace spans for tool calls через OTel/OpenInference-style schema.

### Stream E — Memory / RAG / GraphRAG (P1)
Цель: сделать память не только durable, но и объяснимой.
1. GraphRAG index: nodes/services/logs/experience/errors/decisions.
2. Embedding pipeline на ubu-worker; parent только stores metadata.
3. Query modes: fast (sqlite/vector), deep (GraphRAG), heavy (qwen2.5:7b).
4. Memory proofs: object hash + backend live-read + citation chain.

### Stream F — Audio / VoxRAG (P1)
Цель: довести voice/audio до production.
1. Очередь audio jobs с retry/idempotency.
2. Speaker diarization/voice-id dictionary, manual correction UX.
3. CLAP/audio embeddings → cross-modal links.
4. Store transcript + segments + speaker map in CAS/GraphRAG.

### Stream G — Swarm / BFT / consensus (P1/P2)
Цель: подготовка к 200+ nodes без хаоса.
1. Не масштабировать, пока disk >80% и restart policy не исправлена.
2. BFT/Raft pilot на 4 локальных child, только metadata decisions.
3. Quorum for destructive actions: GC, config push, restart waves.
4. Node reputation использовать только как signal, не как authority.

### Stream H — Observability / OTel / traces (P1)
Цель: из метрик сделать причинность.
1. Добавить trace_id во все scripts/timers/logs.
2. Prometheus остаётся metrics; Loki/logs; добавить Tempo/Jaeger только если disk budget позволяет.
3. Dashboard: restart budget, disk forecast, workflow state, failed timers.
4. Alert dedupe: не спамить при known degraded AWS/free nodes.

### Stream I — CI/CD / GitHub runner / safe deploy (P1)
Цель: любое изменение проверяется до применения.
1. Исправить phase4 Swarm YAML (`placement.constraints` list).
2. GitHub Actions: unit + smoke + service syntax + systemd unit lint.
3. Canary restart: one child → parent → rest children.
4. Auto rollback по test failure.

### Stream J — Free-node expansion / reproduction (P2, gated)
Цель: расширение только бесплатно и с подтверждением.
1. Inventory: Oracle/GCP/Fly/Render/Railway текущие free terms, card requirement.
2. Для каждого ресурса — отдельное approval gate.
3. Prefer ubu-worker/local containers for heavy ML.
4. External free nodes только after P0 green + disk <80%.

## 4. Параллельный запуск — порядок

### Batch R0 — немедленно (уже выполнено)
- Fix restart-loop, subscriber loop, swarm-discovery timeout, Prometheus conflict, tests 16/16.

### Batch R1 — можно запускать параллельно сейчас
- A1: Registry restart_strategy schema + watchdog tests.
- B1: Garage/Docker read-only inventory report.
- I1: fix phase4 YAML + validate stack config.
- H1: trace_id/log correlation spec.

### Batch R2 — после R1 verify
- B2: disk cleanup to <85%, no Garage deletes without read-proof.
- C1: Temporal-lite durable workflow pilot.
- D1: MCP ops server read-only.
- E1: GraphRAG schema and initial index.

### Batch R3 — после disk <80 и P0 green 24h
- F1: VoxRAG production queue.
- G1: local BFT pilot.
- J1: free-tier expansion proposals only, no creation without approval.

## 5. Success metrics
- `octopus test`: 16/16 stable for 24h.
- Failed/autorestart services: 0, excluding benign inactive ones.
- NRestarts key services: 0 or justified.
- Disk: <85% within 24h, <80% target, <75% ideal.
- No parent restart caused by local child watchdog.
- All destructive operations gated by read-proof and human consent.
