# AIOS
Self-evolving distributed operating system for application intelligence, automated testing, API generation, skill evolution and collective learning. Powered by Octopus Runtime.

## Unified repository

Все четыре среза проекта AIOS объединены в единый согласованный набор («best-of-each»):
для каждой темы выбран **один канонический** документ (самый полный), альтернативные
версии сохранены в `variants/` рядом с ним.

### Структура

- `aios_core/` — исполняемый слой (Python, 98 модулей). 12 исходных модулей репозитория
  (`constitution_engine`, `approval_manager`, `memory_manager`, …) сохранены как более полные;
  добавлены модули слоя v2.1.1 из `AIOS-Constitution (2).zip` (`tests/`, `rules.json`,
  `audit_log_schema.json`).
- `docs/aios/` — **единое дерево документации по слоям** (37 слоёв: constitution, core, autonomy,
  intelligence, memory, knowledge, communication, compute, federation, governance, security,
  execution, deployment, monitoring, observability, storage, testing, qa, …). См. `docs/aios/INDEX.md`
  и `docs/aios/README.md`.
- `policies/` — YAML-политики (56): evolution/federation/security исходные + полный набор
  политик слоя v2.1.1.
- `tests/`, `tools/` — тесты и вспомогательные скрипты (в т.ч. `tools/merge_aios_docs.py`).

### Источники (срезы), вошедшие в объединение

| Срез | Что | Версия |
|---|---|---|
| `slice1_native` | каркас репозитория (`docs/core`, `docs/memory`, `docs/constitution`, `constitution/`) | v2.1.1 |
| `slice2_exec_v2_1_1` | манифесты исполняемого слоя (`AIOS-Constitution (2).zip`) | v2.1.1 |
| `slice3_v6` | спецификация Global Federation (`AIOS.zip`) | v6 / v6.1 |
| `slice4_archive_2026` | архитектурный архив 2026 (`AIOS_Archive_2026.zip`) | 2026 (v1–v9) |

> **Срез 4 (`slice4_archive_2026`) — активно развивающийся источник.** Он дополняется дальше
> и считается «живым»: при конфликтах версий одинакового объёма ему отдаётся приоритет, а новые
> материалы слоя 4 интегрируются в `docs/aios/` поверх объединённого набора.

### Как пересобрать объединение

```bash
python3 tools/merge_aios_docs.py   # перечитывает 4 среза и пишет docs/aios/
```
