# AIOS — генерируемый inventory проекта

> Этот файл не редактируется вручную. Источник — Git index/worktree; обновление:
> `python scripts/generate_project_inventory.py --write`.

## Основные метрики

| Метрика | Значение |
|---|---:|
| Package version | `19.9.0` |
| Стабильных tracked-файлов | 6,325 |
| Строк | 608,281 |
| Размер | 24.81 MiB |
| Python-файлов | 3,495 |
| Строк Python | 358,549 |
| Классов / функций / async | 2,984 / 19,821 / 1,636 |
| Python syntax errors | 0 |
| Test Python files / test functions | 953 / 6,648 |
| Markdown-файлов | 2,038 |
| Root `run_*.py` | 113 |
| Уникальных tracked service/timer names | 202 |

## Крупнейшие области

| Область | Файлов | Строк | Размер |
|---|---:|---:|---:|
| `aios_core` | 971 | 158,127 | 5.92 MiB |
| `skills` | 2,641 | 109,481 | 4.73 MiB |
| `docs` | 469 | 75,636 | 3.24 MiB |
| `tests` | 535 | 70,250 | 2.44 MiB |
| `[root]` | 217 | 35,059 | 1.38 MiB |
| `scripts` | 271 | 31,793 | 1.21 MiB |
| `attic` | 33 | 30,669 | 1.61 MiB |
| `octopus_services` | 110 | 27,850 | 0.90 MiB |
| `tg_bot` | 33 | 12,229 | 0.62 MiB |
| `deploy` | 244 | 6,303 | 0.18 MiB |
| `octopus_instructions` | 102 | 5,959 | 0.50 MiB |
| `octopus_roadmap` | 13 | 4,741 | 0.22 MiB |
| `tools` | 46 | 4,441 | 0.15 MiB |
| `converge` | 11 | 4,414 | 0.17 MiB |
| `octopus_projects` | 30 | 3,614 | 0.17 MiB |
| `.github` | 42 | 3,402 | 0.12 MiB |
| `aios_cli` | 15 | 3,389 | 0.13 MiB |
| `octopus_core` | 11 | 2,842 | 0.10 MiB |
| `dashboard` | 8 | 2,483 | 0.55 MiB |
| `octopus_ops` | 23 | 2,223 | 0.06 MiB |

## Основные типы файлов

| Расширение | Файлов |
|---|---:|
| `.py` | 3,495 |
| `.md` | 2,038 |
| `.json` | 147 |
| `.service` | 131 |
| `.timer` | 77 |
| `.sh` | 68 |
| `.tsx` | 65 |
| `.yaml` | 59 |
| `.yml` | 58 |
| `.ts` | 31 |
| `[no-ext]` | 29 |
| `.html` | 12 |
| `.js` | 10 |
| `.conf` | 10 |
| `.ipynb` | 10 |
| `.txt` | 9 |
| `.toml` | 6 |
| `.rst` | 6 |
| `.tf` | 6 |
| `.java` | 5 |

## Compose-роли

- `docker-compose.yml`: 5 services — `aios-core`, `arq-worker`, `postgres`, `redis`, `traefik`
- `docker-compose.unified.yml`: 4 services — `aios_backend`, `aios_frontend`, `grafana`, `prometheus`
- `docker-compose.prod.yml`: 13 services — `aios-alert-canary-receiver`, `aios-api`, `aios-autopilot`, `aios-commercial`, `aios-dashboard`, `aios-exporter`, `aios-mcp`, `aios-p2p`, `aios-telegram-bot`, `aios-telegram-exporter`, `alertmanager`, `grafana`, `prometheus`

Канонические роли и runtime drift: `deploy/DEPLOYMENT_SOURCES.md`.

## Крупнейшие Python-файлы

| Файл | Строк |
|---|---:|
| `aios_core/dashboard.py` | 3,494 |
| `tg_bot/accounts.py` | 3,225 |
| `run_account_control.py` | 2,374 |
| `aios_core/quant_trading_engine.py` | 1,776 |
| `tests/test_v10_4_modules.py` | 1,676 |
| `tests/test_auto_modules.py` | 1,650 |
| `aios_core/api/mixins_core.py` | 1,593 |
| `aios_core/agent_memory_system.py` | 1,574 |
| `run_coder_orchestrator.py` | 1,466 |
| `tests/test_v10_12_modules.py` | 1,445 |
| `run_telegram_bot.py` | 1,409 |
| `tg_bot/phone.py` | 1,308 |
| `tests/test_v10_15_behavioral.py` | 1,274 |
| `tests/test_phase4_test_engine.py` | 1,258 |
| `tg_bot/callbacks.py` | 1,221 |

## Границы

- Исключены `coordination/sessions/`, `coordination/claims/` и сам generated-файл, чтобы параллельные handoff-записи не создавали metric churn.
- Runtime systemd/Docker состояние сюда не входит; используйте `python scripts/audit_deployment_sources.py --runtime`.
- Фактический pytest baseline хранится в `coordination/PROJECT_CONTEXT.md`; inventory считает определения тестов статически.
