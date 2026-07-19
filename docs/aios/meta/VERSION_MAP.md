# AIOS — Карта версий документации

Единая документация `docs/aios/` собрана из нескольких редакций проекта AIOS.
Ниже указано, какая редакция за какие слои отвечает. Это справочная карта
актуального состояния материалов.

## Редакции

| Редакция | Где | Темы |
|---|---|---|
| v2.1.1 (Constitution + Executable Layer) | `core/`, `exec_layer/`, часть `meta/` | ядро, исполняемый слой, манифесты компонентов |
| v6 / v6.1 (Global Federation) | `docs/`, `plans/`, `qa/` | федерация, агентный фреймворк, дорожные карты, QA-ядро |
| 2026 Archive (v1–v9) | все остальные слои: `autonomy`, `intelligence`, `memory`, `memory_advanced`, `knowledge`, `communication`, `compute`, `federation`, `federation_advanced`, `governance`, `governance_advanced`, `identity_trust`, `security`, `security_advanced`, `execution`, `deployment`, `monitoring`, `observability_advanced`, `storage`, `testing` | полная архитектура по слоям |

## Соглашение по версиям в именах файлов
- Суффикс `_v2.1.1` → редакция исполняемого слоя.
- Суффикс `_v6` / `v6_1` → редакция Global Federation.
- Без суффикса в слоях 2026-архива → актуальная редакция.

## Примечание
Разные редакции могут по-разному описывать одни и те же понятия (Memory,
Federation, Governance). При противоречиях приоритет отдаётся актуальной
редакции (2026 Archive); устаревшие формулировки оставлены как исторический
контекст в соответствующих слоях.
