# Сессия: JSON/source tracking policy и краткий формат общения

---
session_id: "20260814T093000Z-aios-arena-tracking-policy"
status: "ACTIVE"
agent: "Arena.ai Agent Mode"
machine: "aios"
started_utc: "2026-08-14T09:30:00Z"
updated_utc: "2026-08-14T09:30:00Z"
branch: "agent/20260814-tracking-policy"
base_commit: "3c166ab1"
claim: "coordination/claims/tracking-policy--20260814T093000Z-aios-arena-tracking-policy.md"
---

## Цель

Убрать опасные глобальные ignore-правила для JSON/source build-каталога, вернуть безопасные manifests в Git и закрепить краткий формат общения агентов с оператором.

## Исходное состояние

- 1 327 ignored JSON; 24 скрыты именно глобальным `*.json`.
- Из 24: 18 runtime/backup/business files должны иметь точечные правила; 6 безопасных manifests/dashboard должны отслеживаться.
- Глобальный `build/` скрывает 41 исходный файл `skills/stitch/build`.
- Redacted scan 47 будущих tracked-файлов: Gitleaks pass, 0 утечек.

## Scope

- Разрешено: `.gitignore`, безопасные source/manifests, policy/checker/tests, `AGENTS.md` communication rule.
- Вне scope: backup JSON, `.llm_keys.json`, warehouse pricelist, Android build outputs, runtime data.

## Следующий шаг

Ввести точечные ignore/unignore правила и автоматическую проверку.
