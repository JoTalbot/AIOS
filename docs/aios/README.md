# docs/aios — Объединённая документация AIOS

Единое дерево, собранное из 4 срезов проекта AIOS по правилу **«best-of-each»**.

## Правила объединения
- Документы сгруппированы по **теме** (нормализованный ключ из имени файла), независимо от
  исходного среза/слоя.
- Для каждой темы выбирается **один канонический** файл — самый полный (по объёму содержимого).
  При равенстве приоритет: `slice4_archive_2026` (живой) > `slice3_v6` > `slice2_exec_v2_1_1` > `slice1_*`.
- Все остальные версии той же темы сохраняются в подпапке `variants/` с префиксом среза:
  `variants/slice3_v6__AIOS_...md`.
- Точные дубликаты (по хешу содержимого) не дублируются.

## Статус среза 4
`slice4_archive_2026` (архив 2026, версии конституции v1–v9) — **активно развивающийся источник**.
Он будет дополняться; новые материалы интегрируются в это дерево поверх объединённого набора.
При равенстве версий ему отдаётся предпочтение как живому.

## Слои (папки)
`constitution`, `core`, `autonomy`, `intelligence`, `memory`, `memory_advanced`, `knowledge`,
`communication`, `compute`, `federation`, `federation_advanced`, `governance`, `governance_advanced`,
`identity_trust`, `security`, `security_advanced`, `execution`, `deployment`, `monitoring`,
`observability_advanced`, `storage`, `testing`, `qa`, `plans`, `roadmaps`, `meta`, а также
`agents`, `applications`, `architecture`, `orchestration`, `planning`, `mcp`, `model`, `skills`,
`foundation`, `reviews`, `docs`, `exec_layer`.

Каждая папка: канонические `*.md` + (опц.) `variants/`.

## Индекс
Полный индекс со срезами-источниками и вариантами — в `INDEX.md` (этой же папки).
Пересборка: `python3 ../../tools/merge_aios_docs.py`.
