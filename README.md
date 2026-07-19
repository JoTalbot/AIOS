# AIOS
Self-evolving distributed operating system for application intelligence, automated testing, API generation, skill evolution and collective learning. Powered by Octopus Runtime.

## Repository layout

- `aios_core/` — исполняемый слой (Python, 98 модулей): ядро конституции, память, управление
  доступом, рассуждение, обучение, оркестрация и прочие компоненты системы (`tests/`,
  `rules.json`, `audit_log_schema.json`).
- `docs/aios/` — единая документация по слоям (37 слоёв: конституция, ядро, автономия,
  интеллект, память, знания, коммуникация, вычисления, федерация, управление, безопасность,
  исполнение, развёртывание, мониторинг, хранилище, тестирование и др.). Указатель — `docs/aios/INDEX.md`.
- `policies/` — YAML-политики системы (эволюция, федерация, безопасность и др.).
- `tests/`, `tools/` — тесты и вспомогательные скрипты.

## Конституция
Действующие статьи и архивные книги конституции — в `docs/aios/constitution/`.

## Версия
`aios_core` (исполняемый слой) — версия **2.1.1**. Целевая платформа и актуальная архитектура описаны редакцией **2026 Archive** (v1–v9) в `docs/aios/`; см. `docs/aios/meta/VERSION_MAP.md`. Единый источник истины по версии — файл `VERSION`.
