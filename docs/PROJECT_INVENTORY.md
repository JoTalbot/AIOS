# AIOS — генерируемый inventory проекта

> Этот файл не редактируется вручную. Источник — Git index/worktree; обновление:
> `python scripts/generate_project_inventory.py --write`.

## Основные метрики

| Метрика | Значение |
|---|---:|
| Package version | `19.9.0` |
| Стабильных tracked-файлов | 6,087 |
| Строк | 556,595 |
| Размер | 22.20 MiB |
| Python-файлов | 3,372 |
| Строк Python | 338,513 |
| Классов / функций / async | 2,957 / 19,144 / 1,630 |
| Python syntax errors | 0 |
| Test Python files / test functions | 921 / 6,539 |
| Markdown-файлов | 1,974 |
| Root `run_*.py` | 113 |
| Уникальных tracked service/timer names | 164 |

## Крупнейшие области

| Область | Файлов | Строк | Размер |
|---|---:|---:|---:|
| `aios_core` | 970 | 157,934 | 5.91 MiB |
| `skills` | 2,641 | 109,481 | 4.73 MiB |
| `tests` | 495 | 66,408 | 2.29 MiB |
| `docs` | 405 | 44,717 | 1.42 MiB |
| `[root]` | 217 | 35,023 | 1.38 MiB |
| `attic` | 33 | 30,669 | 1.61 MiB |
| `octopus_services` | 110 | 27,850 | 0.90 MiB |
| `scripts` | 177 | 15,757 | 0.60 MiB |
| `tg_bot` | 32 | 12,060 | 0.62 MiB |
| `octopus_instructions` | 102 | 5,959 | 0.50 MiB |
| `deploy` | 206 | 5,812 | 0.17 MiB |
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
| `.py` | 3,372 |
| `.md` | 1,974 |
| `.json` | 137 |
| `.service` | 110 |
| `.sh` | 67 |
| `.tsx` | 65 |
| `.timer` | 60 |
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
| `aios_core/quant_trading_engine.py` | 1,768 |
| `tests/test_v10_4_modules.py` | 1,676 |
| `tests/test_auto_modules.py` | 1,650 |
| `aios_core/api/mixins_core.py` | 1,593 |
| `aios_core/agent_memory_system.py` | 1,574 |
| `run_coder_orchestrator.py` | 1,466 |
| `tests/test_v10_12_modules.py` | 1,445 |
| `run_telegram_bot.py` | 1,401 |
| `tg_bot/phone.py` | 1,308 |
| `tests/test_v10_15_behavioral.py` | 1,274 |
| `tests/test_phase4_test_engine.py` | 1,258 |
| `tg_bot/callbacks.py` | 1,221 |

## Границы

- Исключены `coordination/sessions/`, `coordination/claims/` и сам generated-файл, чтобы параллельные handoff-записи не создавали metric churn.
- Runtime systemd/Docker состояние сюда не входит; используйте `python scripts/audit_deployment_sources.py --runtime`.
- Фактический pytest baseline хранится в `coordination/PROJECT_CONTEXT.md`; inventory считает определения тестов статически.
