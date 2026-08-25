# Модель безопасности OpenHands-контура

## Принципы

1. **Наименьшие права** — роль пишет только в `allowed_paths` своего профиля.
2. **Protected не трогаем** — контур не изменяет protected-файлы AIOS
   (`self_protection.PROTECTED_PATTERNS`); проверка в finalize перед PR.
3. **Секреты только в env** — не в коде, не в state-файле, не в логах.
4. **Наблюдаемость** — каждый переход/решение/ошибка в аудите с маскированием.

## Механизмы

| Механизм | Реализация |
|---|---|
| Профили ролей | `permissions.PROFILES`: RBAC-имя, read/write, allowed_paths (glob) |
| Проверка diff | `runner._finalize` → `check_paths(changed_files, profile)`; нарушение → блок COMPLETED |
| Гейты | COMPLETED только при пройденных `required_gates` (state machine, gate-check при переходе) |
| Лимит retry | `max_retries` в `TaskExtras`; исчерпание → CANCELLED + FailureReport (защита от бесконечных циклов) |
| Токен HTTP API | `x-octopus-token` (env `OH_CONTOUR_TOKEN` → `OCTOPUS_TOKEN` → `default`); 401 без токена |
| Маскирование аудита | `OHAuditLogger` поверх канонического `AuditLogger` — секреты не пишутся |
| Git без shell | `GitRunner` — subprocess со списком аргументов (не строка), stderr обрезан, токен не логируется |
| Вердикт-консерватизм | `CHANGES_REQUESTED` побеждает `APPROVED` при обоих маркерах |

## Границы доверия

- Контур доверяет Cloud API только исполнение в sandbox; оркестрация, права и
  аудит остаются в AIOS.
- События разговора — untrusted input: парсинг вердикта только по маркерам,
  без исполнения содержимого.
- State-файл (`oh_contour_tasks.json`) не содержит секретов; битый файл не
  роняет контур (читается как пустой).

## Что НЕ реализовано (риски на владельце)

- Токен по умолчанию `default` — в production задать `OH_CONTOUR_TOKEN`.
- Нет per-user авторизации HTTP API (один токен на сервис, как в octopus).
- Cloud API-ключ читается из env процесса — доступ к процессу = доступ к ключу.
- Реальный прогон против Cloud не выполнялся (тесты на fake-клиенте).
