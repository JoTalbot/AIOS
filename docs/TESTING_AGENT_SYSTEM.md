# Тестирование OpenHands-контура

## Принципы

- **Без моков внешних систем**: git — реальный tmp-репозиторий, HTTP — реальный
  FastAPI TestClient, аудит — реальный `AuditLogger` в tmp-файл, store — реальный
  JSON в tmp_path.
- **Fake только Cloud-клиент**: `tests/test_openhands_runner.py::FakeClient`
  реализует протокол `ConversationClient` (start/wait/events) в памяти — единственная
  граница, которую нельзя исполнить локально без ключа.
- **DI вместо сети**: `GitHubHelper` принимает `pr_opener` — PR-тесты без HTTP.

## Покрытие (139 тестов контура + octopus-регресс)

| Файл | Фаза | Что проверяет |
|---|---|---|
| `test_openhands_client.py` | F1 | Cloud-клиент: конфиг, URL, ошибки, retry, таймауты (DI transport) |
| `test_openhands_models.py` | F2 | Роли, гейты, TaskExtras, FailureReport |
| `test_openhands_permissions.py` | F2 | check_paths против protected/deny, allowed_paths |
| `test_openhands_profiles.py` | F2 | build_prompt: инструкции ролей, self-contained, вердикт-маркер |
| `test_openhands_state_machine.py` | F3 | Таблица переходов, гейты, лимит retry, TransitionError |
| `test_openhands_audit.py` | F3 | События контура, маскирование |
| `test_openhands_github.py` | F5 | GitRunner/Helper на реальном tmp-repo, PR через DI opener |
| `test_openhands_runner.py` | F5 | Lifecycle: happy path, optional gates, retry, deny-paths, PR |
| `test_openhands_service.py` | F6 | ContourService: submit/run/status, канонический маппинг |
| `test_openhands_store.py` | F7 | Round-trip, рестарт, corrupted state, env override |
| `test_openhands_api.py` | F8 | HTTP: auth 401, submit 201/422, flow, 404, failure_report |
| `test_octopus_registry_contour.py` | F4 | Реестр octopus: role/permissions/allowed_paths |

## Ключевые сценарии runner

1. Happy path без GitHub → COMPLETED, гейты tests+review.
2. Опциональные security/qa-гейты включают стадии.
3. 1 падение coder → retry → COMPLETED.
4. Исчерпание лимита → CANCELLED + FailureReport (attempts = 1+retries).
5. `CHANGES_REQUESTED` → BLOCKED → retry → CANCELLED.
6. Deny-paths в diff блокируют COMPLETED.
7. Чистый diff → draft PR, `pr_url`.
8. Аудит-цепочка: каждый переход залогирован.

## Запуск

```bash
python3 -m pytest tests/test_openhands_*.py -p no:cacheprovider   # контур
python3 -m pytest tests/test_octopus_registry_contour.py tests/test_octopus_integration.py  # octopus-регресс
python3 -m ruff check aios_core/openhands/ tests/test_openhands_*.py
```

## Не покрыто

- Реальный OpenHands Cloud (нет ключа в CI) — контракт проверен fake-клиентом
  по `ConversationClient`.
- Конкурентный доступ к state-файлу.
