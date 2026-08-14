# Сессия: канонический deployment source и аудит drift

---
session_id: "20260814T091000Z-aios-arena-deployment-source"
status: "ACTIVE"
agent: "Arena.ai Agent Mode"
machine: "aios"
started_utc: "2026-08-14T09:10:00Z"
updated_utc: "2026-08-14T09:10:00Z"
branch: "agent/20260814-deployment-source"
base_commit: "65c66a8b"
claim: "coordination/claims/deployment-source--20260814T091000Z-aios-arena-deployment-source.md"
---

## Цель

Устранить неоднозначность deployment-источников, не меняя работающий runtime: закрепить канонический production Compose, обезопасить workflows/scripts и добавить воспроизводимый drift-аудит.

## Scope

- Разрешено: deploy documentation, workflows, deployment helper scripts, новый read-only audit tool и тесты.
- Вне scope: содержимое protected compose YAML, удаление/перезапуск systemd units, credentials, service restart.
- Работа выполняется в отдельном worktree.

## Исходное состояние

- Docker labels работающих контейнеров подтверждают `/root/AIOS/docker-compose.prod.yml` как фактически используемый production Compose.
- `docker-compose.prod.yml` имеет 68 ссылок и используется SSH/full-CI deployment.
- `.github/workflows/deploy.yml` вызывает `docker compose` без `-f`, что при настроенных secrets выбрало бы неканонический `docker-compose.yml`.
- `deploy/production/docker-compose.prod.yml` — отличающийся старый v9.1 stack.
- В Git 50 уникальных active-intent unit names, на хосте установлено 159 AIOS unit files; 116 установленных имён не отслеживаются.
- Нельзя автоматически удалять untracked units: сначала ownership и secret review.

## План

1. Закрепить роли всех Compose-файлов в документации и автоматической проверке.
2. Исправить deploy workflow на явный canonical `-f docker-compose.prod.yml`.
3. Пометить local/all-in-one и experimental swarm scripts, исключив случайный production use.
4. Добавить read-only audit tool для tracked/runtime drift и тесты.
5. Не изменять runtime; записать безопасный план reconciliation.

## Проверки

- `[NOT RUN]` — реализация ещё не начата.

## Handoff

- Последняя завершённая точка: read-only inventory.
- Следующий шаг: реализовать статический audit contract.
- Блокеры: нет.
