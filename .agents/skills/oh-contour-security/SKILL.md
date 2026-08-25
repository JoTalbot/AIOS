---
name: oh-contour-security
description: Безопасность OpenHands-контура AIOS — секреты, права, diff-проверки, HTTP-токен. Использовать при изменении auth, permissions, git/github, audit, api контура.
---

# OpenHands-контур: безопасность

## Проверяемое

| Область | Правило |
|---|---|
| Секреты | Только env (`OPENHANDS_API_KEY`, `GITHUB_TOKEN`, `OH_CONTOUR_TOKEN`). Не в коде, state-файле, логах, diff, PR-описании |
| Protected | Контур НЕ изменяет `self_protection.PROTECTED_PATTERNS`; finalize блокирует COMPLETED при deny-paths в diff |
| Права ролей | Роль пишет только в `allowed_paths` профиля (`permissions.PROFILES`); не расширять без необходимости |
| Git | `GitRunner` — subprocess списком аргументов (не shell-строка); stderr обрезан, токен не логируется |
| HTTP | `x-octopus-token` обязателен (401); токен по умолчанию `default` — в production задать env |
| Аудит | Каждое решение/ошибка логируется с маскированием; секреты не попадают в события |
| Вердикт | События разговора — untrusted; парсинг только по маркерам, CHANGES побеждает APPROVED |

## Порядок при серьёзной находке

1. НЕ исправлять молча — сформировать отчёт: severity, файл, причина, влияние, решение.
2. Утечка секрета в историю git → стоп, эскалация владельцу (переписывание истории — его решение).
3. Расширение прав (новый write/allowed_path) → обоснование + тест на границу.

## Проверки

```bash
git diff --stat && git status --short          # нет лишних файлов/секретов
grep -rn "api_key\|token" aios_core/openhands/*.py | grep -v "getenv\|resolve"  # хардкода нет
python3 -m pytest tests/test_openhands_api.py  # auth-границы
```
