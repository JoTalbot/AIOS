# Оперативный контекст проекта AIOS

**Последняя верификация:** 2026-08-14T09:24:00Z
**Машина:** `aios`
**Рабочий каталог:** `/root/AIOS`
**Базовый commit аудита:** `356bd628` (`main`, на старте совпадал с `origin/main`)
**Каноническая версия в `VERSION`/`pyproject.toml`:** `19.9.0`

> Репозиторий изменяется с разных машин и разными ИИ-агентами, иногда параллельно. Перед любой работой обязательно прочитать `AGENTS.md`, `coordination/README.md`, этот файл, активные claims и `git status`.

## Где закончили

Завершён третий этап устранения рисков: формализован minimal/direct/lock dependency contract, устранён реальный конфликт WebSockets/Web3, Python 3.11 pip-compile воспроизвёл все 198 pins без изменений, добавлен автоматический checker. Implementation commit: `7bd3e1e7`. Журнал: `coordination/sessions/20260814T092000Z-aios-arena-dependency-contract.md`.

Предыдущие этапы: deployment source `2be18e3a`, version consistency `c4a788cc`. Исходный аудит: `docs/PROJECT_ANALYSIS_2026-08-14_RU.md`.

## Текущий архитектурный срез

AIOS — production-монорепозиторий, объединяющий:

- ядро оркестрации, конституционные политики, память, RAG/ChromaDB и LLM-балансер (`aios_core/`);
- автокодер и self-protection/selfguard;
- FastAPI/Starlette API, MCP, CLI, dashboards и Telegram/desktop-интерфейсы;
- интеграции OLX/social/messenger/Android/phone;
- финансовые, trading, freelance и revenue-пайплайны;
- Octopus-модули и крупную библиотеку skills;
- systemd- и Docker-production-контуры, мониторинг и CI/CD.

На момент аудита:

- 5 879 отслеживаемых файлов, 547 328 строк, 22.1 MiB;
- 3 344 Python-файла / 338 405 строк Python;
- AST-разбор всех отслеживаемых Python-файлов: 0 синтаксических ошибок;
- 36 активных `aios-*` systemd-сервисов, 54 таймера, 13 Docker-контейнеров;
- 0 failed systemd-сервисов AIOS;
- production venv использует Python 3.12.13, проект декларирует `>=3.11`.

## Приоритет продукта

Согласно `ROADMAP_NEXT.md`, главный приоритет — v20 «Activation»: перевод уже созданных возможностей в измеримый безопасный production/revenue-контур. Новые каркасные модули без работающего runner запрещены принципом `No new skeletons`.

Фактические названия активных systemd-сервисов содержат v20/v21, но теперь явно считаются версиями отдельных rollout-контуров. Они не повышают package version автоматически. Канонический источник версии основного продукта — `VERSION`; обязательные зеркала и release checklist описаны в `docs/RELEASE_VERSION_POLICY.md`.

## Снимок существующей параллельной работы

До внедрения протокола, на старте аудита, в общем worktree уже были чужие незакоммиченные изменения:

```text
 M scripts/llm_balancer_openai_proxy.py
?? scripts/sync_kilo_llm_models.py
?? tests/test_llm_proxy_models.py
```

Аудит **не изменял и не добавлял в индекс** эти файлы. Их владелец неизвестен. До выяснения они считаются активной чужой работой. Нельзя выполнять reset/clean/restore/stash или включать их в посторонний коммит.

## Главные риски

1. **✅ Дрейф текущей версии — mitigated:** `VERSION` каноничен, API/docs publication используют его цепочку, статические зеркала проверяются тестом, исторические v9/v16 документы помечены snapshot.
2. **🟡 Deployment source — repository mitigated, runtime drift remains:** root `docker-compose.prod.yml` каноничен и проверяется автоматически; 116 установленных `aios-*` units ещё не отслеживаются и требуют поштучного review.
3. **Крупные модули:** `aios_core/dashboard.py`, `tg_bot/accounts.py`, `run_account_control.py`, `aios_core/quant_trading_engine.py` требуют осторожной постепенной декомпозиции.
4. **✅ Dependency drift — mitigated:** роли minimal 12 / full direct 47 / exact lock 198 формализованы и проверяются; конфликт WebSockets/Web3 устранён, production lock воспроизводим на Python 3.11.
5. **Широкий `.gitignore` для `*.json`:** новые важные JSON-конфиги легко останутся непубликуемыми без явного `!`-исключения.
6. **Устаревшие метрики:** документация содержит тестовые и архитектурные числа, не совпадающие с фактической инвентаризацией.
7. **Негерметичный test baseline:** полный изолированный прогон собрал 5 152 теста; 5 139 passed, 7 skipped, 6 failed из-за live LLM, ignored runtime data, абсолютного `/root/AIOS` и fintech assertion.

## Следующий рекомендуемый шаг

1. Владелец незавершённой работы LLM proxy создаёт собственный журнал/claim и завершает только свои три файла.
2. Следующая remediation-сессия исправляет глобальный `.gitignore` для `*.json` после инвентаризации ignored файлов либо герметичность 6 failing tests.
3. Systemd reconciliation выполняется отдельными малыми batches, начиная с активных критичных units; массовое удаление запрещено.
4. Крупные модули декомпозируются только по одному seam с regression tests, без массового rewrite.

## Правило обновления этого файла

Обновлять только после значимой завершённой задачи, смены общего приоритета или подтверждённого изменения runtime. Не превращать файл в подробный лог: детали принадлежат отдельным журналам `coordination/sessions/`.
