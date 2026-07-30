# SKILLS DEEP AUDIT — честная классификация 243 скиллов
*2026-07-16 · ZCode · независимый аудит (read-only)

> Контекст: инструкция №31 декларирует «нуль заглушек» и grade S в `skills_health.json`.
> Этот аудит проверяет содержательную наполненность, а не только наличие секций.

## Сводка

| Tier | Кол-во | Доля | Что это |
|---|---|---|---|
| **REAL** | 13 | 5% | Уникальный алгоритм + реальный код + тесты |
| **HYBRID** | 70 | 28% | Частично: либо уникальный алгоритм при тонком коде, либо реальный код при шаблонном алгоритме |
| **SCAFFOLD** | 160 | 65% | Шаблонный каркас: 7-строчный универсальный «Алгоритм» + тонкий `run.py`-обёртка + шаблонный тест |
| **Всего** | **243** | 100% | |

### По категориям

| Категория | REAL | HYBRID | SCAFFOLD | Всего |
|---|---|---|---|---|
| core | 4 | 9 | 119 | 132 |
| memory | 2 | 28 | 2 | 32 |
| swarm | 1 | 31 | 2 | 34 |
| meta | 6 | 2 | 29 | 37 |
| research | 0 | 0 | 4 | 4 |
| dr | 0 | 0 | 2 | 2 |
| mcp | 0 | 0 | 2 | 2 |

## Ключевой вывод

**91% скиллов (221 из 243) содержат один и тот же шаблонный «Алгоритм»** —
7-строчный универсальный текст, не связанный с назначением скилла.
Loader v3 считает их не-заглушками, потому что проверяет только *наличие* секций,
а не их *содержание*. `skills_health.json` (grade S, stubs 0) формально прав,
но содержательно вводит в заблуждение.

Дополнительно: `skills_health.json` видит **177** скиллов из 243 —
категории `memory/` (32) и `swarm/` (34) полностью вне мониторинга здоровья.

## REAL — реально реализованные (13)

| Score | Skill | Код | Тесты | Refs |
|---|---|---|---|---|
| 100 | `core/money-earner-orchestrator` | 10055L (60 файлов) | 384L / 43fn | 4 |
| 100 | `meta/skill-health-monitor` | 131L (2 файлов) | 47L / 5fn | 5 |
| 100 | `meta/skill-notification` | 223L (2 файлов) | 41L / 5fn | 5 |
| 100 | `meta/skill-task-decompose` | 174L (2 файлов) | 47L / 5fn | 4 |
| 100 | `swarm/resource-coexistence` | 321L (1 файлов) | 116L / 19fn | 2 |
| 90 | `core/graphrag-exact-citations` | 82L (2 файлов) | 36L / 3fn | 3 |
| 88 | `meta/skill-schedule-runner` | 115L (2 файлов) | 22L / 3fn | 5 |
| 88 | `meta/skill-web-dashboard` | 191L (2 файлов) | 22L / 3fn | 5 |
| 78 | `memory/archived-report-resurrection-reconciler` | 167L (1 файлов) | 52L / 2fn | 1 |
| 78 | `memory/strict-iter-archive-gate` | 163L (1 файлов) | 41L / 2fn | 0 |
| 78 | `meta/skill-usage-audit` | 79L (1 файлов) | 41L / 2fn | 2 |
| 70 | `core/agent-recovery-grant-guard` | 26L (2 файлов) | 22L / 3fn | 4 |
| 70 | `core/dr-config-preflight` | 12L (1 файлов) | 50L / 5fn | 4 |

## HYBRID — кандидаты на доработку (70)

Две подкатегории:

### A. Уникальный алгоритм, но тонкий код (9) — ближе всего к REAL

| Skill | Код | Тесты |
|---|---|---|
| `core/all-vectors-orchestrator` | 12L | 14L / 2fn |
| `core/autopilot-runtime-durability-guard` | 12L | 22L / 3fn |
| `core/consent-gate-enforcer` | 12L | 22L / 3fn |
| `core/octopus-autoheal` | 12L | 22L / 3fn |
| `core/orphan-session-drift-guard` | 12L | 22L / 3fn |
| `core/secrets-hygiene-audit` | 12L | 22L / 3fn |
| `core/telegram-noise-auditor` | 12L | 22L / 3fn |
| `meta/skill-telegram-control-panel` | 12L | 17L / 2fn |

### B. Шаблонный алгоритм, но реальный код (61) — в основном memory/ и swarm/

| Skill | Категория | Код | Тесты |
|---|---|---|---|
| `core/integration-testing` | core | 117L | 22L/3fn |
| `core/web-research` | core | 124L | 22L/3fn |
| `meta/skill-autonomous-agent` | meta | 555L | 22L/3fn |
| `memory/archive-rotation-reader` | memory | 52L | 22L/3fn |
| `memory/cas-integrity-reader` | memory | 52L | 22L/3fn |
| `memory/cas-pack-guard` | memory | 52L | 22L/3fn |
| `memory/cas-replication-guard` | memory | 52L | 22L/3fn |
| `memory/dna-shard-audit` | memory | 52L | 22L/3fn |
| `memory/dna-sharding-guard` | memory | 52L | 22L/3fn |
| `memory/immortal-memory-orchestrator` | memory | 44L | 22L/3fn |
| `memory/ipfs-pin-audit` | memory | 52L | 22L/3fn |
| `memory/memory-immortal-guard` | memory | 44L | 22L/3fn |
| `memory/memory-ipfs-exporter` | memory | 52L | 22L/3fn |
| `memory/memory-merkle-guard` | memory | 52L | 22L/3fn |
| `memory/memory-retrieval-quality` | memory | 44L | 22L/3fn |
| `memory/memory-systems` | memory | 44L | 22L/3fn |
| `memory/merkle-auto-monitor` | memory | 52L | 22L/3fn |
| `memory/octopus-archive-rotate` | memory | 52L | 22L/3fn |
| `memory/octopus-ipfs-pin-coordinator` | memory | 52L | 22L/3fn |
| `memory/octopus-memory-coverage-alert` | memory | 52L | 22L/3fn |
| `memory/octopus-memory-dashboard` | memory | 52L | 22L/3fn |
| `memory/octopus-memory-drill-api` | memory | 52L | 22L/3fn |
| `memory/octopus-memory-exporter` | memory | 52L | 22L/3fn |
| `memory/octopus-memory-gc-dryrun` | memory | 52L | 22L/3fn |
| `memory/octopus-memory-indexer` | memory | 52L | 22L/3fn |
| `memory/octopus-memory-manifest` | memory | 52L | 22L/3fn |
| `memory/octopus-memory-replicator` | memory | 52L | 22L/3fn |
| `memory/octopus-memory-restore-alert` | memory | 52L | 22L/3fn |
| `memory/octopus-memory-restore-drill` | memory | 52L | 22L/3fn |
| `memory/octopus-memory-restore-drill-ec2` | memory | 52L | 22L/3fn |
| `memory/octopus-pack-read-guard` | memory | 52L | 22L/3fn |
| `swarm/auto-reproduction` | swarm | 43L | 22L/3fn |
| `swarm/barter-policy-enforcer` | swarm | 50L | 22L/3fn |
| `swarm/bft-consensus` | swarm | 43L | 22L/3fn |
| `swarm/bft-lite` | swarm | 43L | 22L/3fn |
| `swarm/bft-lite-validator` | swarm | 43L | 22L/3fn |
| `swarm/consensus-heartbeat` | swarm | 43L | 22L/3fn |
| `swarm/cross-swarm-voting` | swarm | 43L | 22L/3fn |
| `swarm/federated-event-bus` | swarm | 43L | 22L/3fn |
| `swarm/geo-aware-routing` | swarm | 43L | 22L/3fn |
| `swarm/geo-latency-resolver` | swarm | 43L | 22L/3fn |
| `swarm/inter-swarm-collab` | swarm | 43L | 22L/3fn |
| `swarm/node-capability-advertiser` | swarm | 50L | 22L/3fn |
| `swarm/node-health-orchestrator` | swarm | 43L | 22L/3fn |
| `swarm/node-reputation` | swarm | 50L | 22L/3fn |
| `swarm/node-reputation-reader` | swarm | 50L | 22L/3fn |
| `swarm/p2p-federation` | swarm | 43L | 22L/3fn |
| `swarm/reproduction-guard` | swarm | 43L | 22L/3fn |
| `swarm/resource-barter` | swarm | 50L | 22L/3fn |
| `swarm/self-replication-validator` | swarm | 43L | 22L/3fn |
| `swarm/swarm-coordination` | swarm | 43L | 22L/3fn |
| `swarm/swarm-discovery` | swarm | 43L | 22L/3fn |
| `swarm/swarm-discovery-protocol` | swarm | 43L | 22L/3fn |
| `swarm/swarm-health-guard` | swarm | 43L | 22L/3fn |
| `swarm/swarm-load-forecaster` | swarm | 43L | 22L/3fn |
| `swarm/swarm-reasoning` | swarm | 43L | 22L/3fn |
| `swarm/swarm-reasoning-hub` | swarm | 43L | 22L/3fn |
| `swarm/swarm-reproduction` | swarm | 43L | 22L/3fn |
| `swarm/swarm-resource-barter` | swarm | 50L | 22L/3fn |
| `swarm/swarm-version-checker` | swarm | 50L | 22L/3fn |
| `swarm/swarm-voting` | swarm | 43L | 22L/3fn |
| `swarm/vote-weight-calculator` | swarm | 43L | 22L/3fn |

Всего в группе B: 62

## SCAFFOLD — шаблонные каркасы (160)

Это массово сгенерированные заглушки с одинаковым наполнением.
Из них 158 имеют идентичную сигнатуру тестов (22 строки / 3 функции).
По №27/№31 они должны быть либо доработаны, либо удалены/заархивированы.

### Распределение по категориям

- **core**: 119
- **meta**: 29
- **research**: 4
- **memory**: 2
- **swarm**: 2
- **dr**: 2
- **mcp**: 2

## Найденные проблемы

1. **Иллюзия метрик.** `Stubs: 0` / `grade S` не отражают реального состояния.
2. **Слепота мониторинга.** `skills_health.json` не обходит `memory/` и `swarm/` (66 скиллов).
3. **Захламление бэкапами.** `money-earner-orchestrator/code/` содержит десятки `.bak` файлов прямо в `code/` (должны быть в `_reorg_backups/` или `archive/`).
4. **Шаблонные тесты.** 158 скиллов имеют тест 22L/3fn — почти наверняка копия одного шаблона.
5. **`skill-autonomous-agent`** (meta) имеет 555 строк кода, но **нет секции Алгоритм** (missing) — формальная заглушка-документ.

## Рекомендации

1. **Доработать критерий loader/health** — учитывать шаблонность алгоритма,
   не только наличие секций. Тогда `stubs` будет отражать реальность.
2. **Починить сканер здоровья** — добавить `memory/` и `swarm/` в обход.
3. **Заархивировать 158 одинаковых SCAFFOLD-каркасов** или промаркировать как
   `status: scaffold` (а не Active) — чтобы не вводить в заблуждение.
4. **Перенести `.bak` из `money-earner-orchestrator/code/` в архив.**
5. **Сфокусироваться** на доработке 9 HYBRID-группы-A (у них уже уникальный алгоритм)
   и сохранении качества 13 REAL.
---

*Скрипт аудита: `/tmp/skill_audit.py` · JSON-результат: `/tmp/skill_audit_result.json`*

---

## ВЕРИФИКАЦИЯ (2026-07-16, follow-up)
Критерий «настоящий скилл»: покрывает реальную боевую задачу системы И исполняется
(run.py отдаёт осмысленный результат, тесты проходят). Фактическая проверка 257 скиллов
+ прогон `loader/generic_skill_runtime.py` вживую.

**Уточнения к выводам выше (важно перед любым удалением/архивацией):**
- Пункт 1 (91% одинаковый «Алгоритм») — методологически неточен. Шаблон
  `1. Собрать входные данные` отсутствует (0 совпадений). Реально частый алгоритм
  («загрузить SKILL.md → классифицировать → read-only → JSON») встречается 205 раз, но это
  осмысленный алгоритм работы через `generic_skill_runtime`, а не пустышка.
- «160 SCAFFOLD-заглушек» — **ложная категория**. 142 скилла используют
  `generic_skill_runtime` (242 строки, read-only, рабочий) и исполняются корректно
  (проверено: `core/agent-recovery-grant-guard` выдаёт валидный JSON-контракт). Плюс 115 —
  с собственным кодом. Итого 257 **рабочих** скиллов. Их удаление/архивация СЛОМАЕТ вызовы
  из автоагента (нарушение №34/№48 skills-first).
- Пункт 2 (слепота health к memory/swarm) — **ВЕРНО**. Исправлено 2026-07-16: в
  `scripts/skill_evolution_cycle.py` CATEGORIES дополнен `memory`,`swarm`; `skills_health.json`
  пересобран, `total` = 257 (было 189), memory(34)+swarm(34) теперь в мониторинге.
- Пункт 3 («десятки .bak в code/» money-earner) — преувеличено: фактически **1** файл.
  Перенесён в `core/money-earner-orchestrator/_reorg_backups/` (2026-07-16).
- Пункт 5 (`skill-autonomous-agent` «нет Алгоритм») — **ОШИБКА**: секция
  `## Алгоритм (цикл каждые 30 минут)` присутствует (строка 16).

**Итог:** ядро (много шаблонных по форме скиллов) верно, но вывод «удалить/заархивировать 160
SCAFFOLD» некорректен. Дорабатывать — через углублённую классификацию по покрытию векторов №53,
а не через удаление рабочих generic-скиллов. Детали: `reports/skill_analysis_verification_2026-07-16.md`.
