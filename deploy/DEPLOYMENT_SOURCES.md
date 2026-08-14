# Источники deployment-конфигурации AIOS

## Канонический production Compose

Единственный канонический Docker Compose для production:

```text
docker-compose.prod.yml
```

Работающие контейнеры `aios-api`, `aios-mcp`, `aios-dashboard` и monitoring stack имеют Docker label `com.docker.compose.project.config_files=/root/AIOS/docker-compose.prod.yml`, что подтверждено read-only аудитом 2026-08-14.

Любая production-команда обязана указывать файл явно:

```bash
docker compose -f docker-compose.prod.yml config -q
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Использование голого `docker compose up` в production запрещено: оно неявно выбирает `docker-compose.yml`.

## Роли остальных Compose-файлов

| Файл | Роль | Разрешённое использование |
|---|---|---|
| `docker-compose.prod.yml` | `canonical-production` | Production, CI health/e2e, SSH deployment |
| `docker-compose.yml` | `local-integration` | Локальная Traefik/Postgres/Redis разработка; не production |
| `docker-compose.unified.yml` | `experimental-swarm-ui` | Экспериментальный UI/Swarm только с явным opt-in |
| `deploy/production/docker-compose.prod.yml` | `legacy-v9-reference-only` | Исторический v9.1 reference; не запускать |

Legacy-файл намеренно пока не удаляется: Compose-файлы защищены `AGENTS.md`, а удаление требует отдельного review миграций и ссылок. Автоматический аудит предупреждает, что legacy и canonical содержимое различается.

## Deployment entrypoints

- `.github/workflows/deploy.yml` — manual-only применение канонического root Compose; не запускается на каждый push.
- `.github/workflows/full-ci-cd.yml` — gated production path; использует `docker-compose.prod.yml` после проверок.
- `scripts/deploy_ssh.sh` — ручной SSH deployment канонического Compose.
- `.github/workflows/deploy-ssh.yml` — manual-only `git pull`, сам сервисы не перезапускает.
- `deploy-all-in-one.sh` — только local/demo stack и Android emulator.
- `scripts/deploy_swarm.sh` — экспериментальный Swarm; требует `AIOS_ALLOW_EXPERIMENTAL_SWARM=1`.

Workflow с названием `Build & Auto-Deploy to VPS` до этого аудита завершался статусом success, когда job deployment был **skipped** из-за отсутствующих secrets. Статус workflow нельзя интерпретировать как факт production rollout без проверки jobs.

## Systemd desired state и drift

На 2026-08-14:

- в Git: 48 уникальных `aios-*` unit names (50 вместе с двумя Octopus units);
- установлено на хосте: 159 AIOS unit files;
- установлено, но не отслеживается: 116 имён;
- tracked, но не установлено: 7 имён.

Это означает, что systemd desired state пока **не полностью воспроизводим из Git**. Нельзя автоматически удалять 116 units: среди них активные revenue, phone, LLM и monitoring процессы, а unit-файлы могут требовать secret review.

Безопасный reconciliation:

1. Снять read-only inventory.
2. Для каждого untracked unit определить owner, runner, секреты, активность и replacement.
3. Redact и перенести нужный unit в `deploy/systemd/` отдельным малым коммитом.
4. Для ненужного unit сначала disable/observe в согласованное окно, затем удалить отдельной операцией.
5. Никогда не выполнять массовый `systemctl disable --now` по результату одного diff.

## Read-only аудит

```bash
source /opt/aios/.venv/bin/activate
python scripts/audit_deployment_sources.py --strict
python scripts/audit_deployment_sources.py --runtime
```

Первая команда проверяет repository contract и безопасна для CI. Вторая дополнительно читает systemd/Docker metadata, но ничего не изменяет.

Чтобы намеренно сделать runtime drift блокирующим:

```bash
python scripts/audit_deployment_sources.py --runtime --strict --fail-on-runtime-drift
```

Сейчас последний режим ожидаемо завершится non-zero, пока 116 unmanaged units не будут разобраны по одному.
