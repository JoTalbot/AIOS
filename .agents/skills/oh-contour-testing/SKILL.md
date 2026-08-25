---
name: oh-contour-testing
description: Тестирование OpenHands-контура AIOS — принципы без моков, fake-клиент, сценарии runner. Использовать при написании/запуске тестов tests/test_openhands_*.py.
---

# OpenHands-контур: тестирование

## Принципы

- Без моков внешних систем: git — реальный tmp-репозиторий, HTTP — реальный
  FastAPI TestClient, аудит — реальный `AuditLogger` в tmp, store — реальный JSON.
- Fake только Cloud-клиент: `tests/test_openhands_runner.py::FakeClient`
  (протокол `ConversationClient` в памяти) — единственная граница без ключа.
- DI вместо сети: `GitHubHelper(pr_opener=...)`, `OpenHandsClient(transport=...)`.
- Env-изоляция: `monkeypatch` на модульных атрибутах/env; state — в `tmp_path`.

## Стандартные фикстуры

```python
from tests.test_openhands_runner import FakeClient  # fake-клиент по протоколу runner
# store: ContourStore(state_dir=tmp_path); api: contour_api.set_service(service)
```

## Обязательные сценарии при изменении lifecycle

1. Happy path → COMPLETED с гейтами.
2. Опциональные гейты включают security/qa-стадии.
3. Падение стадии → retry → COMPLETED; исчерпание лимита → CANCELLED + FailureReport.
4. `CHANGES_REQUESTED` → BLOCKED.
5. Deny-paths в diff блокируют COMPLETED.
6. Аудит-цепочка каждого перехода.

## Запуск

```bash
python3 -m pytest tests/test_openhands_*.py -p no:cacheprovider   # контур
python3 -m pytest tests/test_octopus_registry_contour.py         # octopus-регресс
python3 -m ruff check aios_core/openhands/ tests/test_openhands_*.py
```

Отчёт: passed/failed/skipped + оставшиеся риски. Не закрывать фазу при failed.
