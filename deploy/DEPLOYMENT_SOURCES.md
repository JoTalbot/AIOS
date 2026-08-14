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

Snapshot 2026-08-14 reconciled:

- 159 установленных `aios-*` unit names представлены в Git;
- 114 ранее отсутствовавших regular base units импортированы без применения к runtime;
- 3 masked units сохранены в `HETZNER_MASKED_UNITS.txt`;
- 9 drop-ins отслеживаются;
- 2 отличающихся base units сохранены как exact Hetzner host overrides без ухудшения canonical definitions;
- 5 host-native units считаются optional-not-installed на Docker profile.

Структура и правила применения: `deploy/systemd/README.md`. Strict runtime audit сравнивает names, base hashes, drop-ins, masks, optional profile и Compose labels. Import был read-only: `daemon-reload`, enable/disable/restart не выполнялись.

Любое будущее применение unit-файлов — отдельная operator-approved операция с `systemd-analyze verify`, backup, rollout и rollback. Массовые `systemctl disable --now`, restart или remove запрещены.

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

После reconciliation этот режим должен завершаться zero на текущем Hetzner profile.
