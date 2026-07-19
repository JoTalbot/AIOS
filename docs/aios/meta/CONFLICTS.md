# AIOS — Конфликты редакций

Документация `docs/aios/` собрана из нескольких редакций (v2.1.1, v6/v6.1,
2026 Archive). Ниже зафиксированы известные смысловые расхождения и выбранный
единственный источник истины.

## Memory
- **v2.1.1** (`core/AIOS_MEMORY_ARCHITECTURE.md`): память как «структурированный
  опыт» (Observation→Experience→Memory Formation→Knowledge→Planning).
- **2026 Archive** (`memory_advanced/`): явное разделение на short/long/semantic/
  episodic память, индексация, сжатие, версионирование.
- **Решение**: актуальная модель — 2026 Archive (явные типы памяти); v2.1.1
  оставлена как концептуальная основа.

## Federation
- **v6/v6.1** (`docs/AIOS_FEDERATION_ARCHITECTURE.md`): Global Federation,
  агентная координация.
- **2026 Archive** (`federation/`, `federation_advanced/`): узлы, P2P, консенсус,
  swarm, глобальный state-manager.
- **Решение**: 2026 Archive — полная спецификация; v6 оставлена как
  исторический контекст агентного фреймворка.

## Governance / Approval
- Разные редакции по-разному описывают порог человеческого надзора.
- **Решение**: единый источник — `policies/governance_policy.yaml` +
  `approval_manager.py` (scope `global`/`constitution` и high-risk требуют
  подтверждения).

## Версия кода
- Код `aios_core` маркирован версией `2.1.1`, хотя документация доходит до 2026/v9.
- **Решение**: `2.1.1` — версия исполняемого слоя; целевая платформа описана
  редакцией 2026 Archive. См. `VERSION_MAP.md`.
