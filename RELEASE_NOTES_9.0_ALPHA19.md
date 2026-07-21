# AIOS 9.0.0-alpha.19 — lease TTL, встроенные джобы, pacing, own-promote

**Дата:** 2026-07-21 · **Тесты:** 892/892 зелёные

Весь H1-блок роадмапа закрыт параллельными батчами: очереди закалены
под отказы нод, джобы покрывают весь эксплуатационный набор, циклы
температурят как человек, застоявшиеся посты получают guarded-план
продвижения.

## Что нового

### ⏱ Job lease TTL (ShardExec)
- `heartbeat(host)` — воркер отмечается на каждом `work_once`.
- `requeue_stale(ttl)` — зависшие claimed-джобы возвращаются в pending
  (host снимается, sticky-маршрут переоценится при следующем claim).
- `stats()` — глубина очереди, счётчики по статусам, `stale_claimed`,
  карта heartbeat'ов.

```bash
aios shards jobs --stats            # queue depth / stale
aios shards requeue-stale --ttl 600
```

### 🧩 Встроенные виды джоб
`default_handlers`: `autopilot`, `reels` (--open-tab), `dm-flush`,
`marker-check` — guarded shell-out в aios_cli, `payload.args`
добавляет флаги:

```bash
aios shards enqueue --profile instagram:main --kind reels \
    --payload '{"args": ["--max", "50"]}'
aios shards enqueue --profile instagram:main --kind marker-check
```

### 🐢 Human-like pacing (`platforms/pacing.py`)
`Pacer`: рандомизированный jitter перед действием, квота
actions/hour скользящим окном, лимит сессии. Исчерпание — честный
стоп цикла, не обход. Встроен в OLXCollector (→ InstagramCollector)
и ReelsCollector; `pacer_from_limits` читает per-profile квоты из
pool kv. Первый сигнал бана — «too fast»; теперь он исключён
конфигурацией:

```bash
aios instagram autopilot --login --pace-actions 40 --pace-jitter 2.0
```

### 📣 Own-promote (DRY-RUN)
`promotion_plan`: stagnant-анализ → план продвижения (кандидаты,
равномерный дневной бюджет, действие boost). Промоут-флоу не
имитируется — честный `dry_run`, webhook-предложение
`promote-suggestion`:

```bash
aios instagram autopilot --login --own --promote --promote-budget 150
```

## Проверка
- **892 автотеста** (879 + 13 новых: TTL/requeue/stats/heartbeats,
  builtin kinds shell-out, Pacer/квоты/окно/сессия, pacing в
  коллекторах, promote plan/CLI).
- Документация: `docs/ROADMAP_FULL.md` (H1.1–H1.4 ✅),
  `docs/PLATFORMS_SCALING.md`, `CHANGELOG.md`.

## Артефакты
- `aios-9.0.0a19-py3-none-any.whl`
- `aios-9.0.0a19.tar.gz`
