# Оперативный контекст проекта AIOS

**Последняя верификация:** 2026-08-14T11:23:03Z
**Машина:** `aios`
**Рабочий каталог:** `/root/AIOS`
**Базовый commit аудита:** `356bd628` (`main`, на старте совпадал с `origin/main`)
**Каноническая версия в `VERSION`/`pyproject.toml`:** `19.9.0`

> Репозиторий изменяется с разных машин и разными ИИ-агентами, иногда параллельно. Перед любой работой обязательно прочитать `AGENTS.md`, `coordination/README.md`, этот файл, активные claims и `git status`.

## Где закончили

Завершена оставшаяся LLM proxy/Kilo работа: catalog/routing/tool calls/SSE/Colab guards и atomic model sync протестированы и развернуты; proxy healthy, 36 моделей, полный suite 5 174 passed / 7 skipped / 0 failed. Implementation commit: `39bec522`. Журнал: `coordination/sessions/20260814T110305Z-aios-arena-llm-proxy-takeover.md`.

Предыдущие этапы: runtime hygiene `a08eb6a8`, quant seam `c2a0bb55`, systemd reconciliation `127c09ea`, inventory stability `42ba5e15`/`f6ada673`.

Предыдущие этапы: test hermeticity `201df1eb`, tracking policy `b75c7c14`, dependency contract `7bd3e1e7`, deployment source `2be18e3a`, version consistency `c4a788cc`.

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

## Текущая параллельная работа

На момент верификации активных claims и незакоммиченных файлов нет. Последняя историческая dirty LLM proxy работа завершена в `39bec522`. Перед новой задачей всё равно проверять `coordination/claims/` и `git status`.

## Runtime operator decisions

- `2026-08-14T11:23:03Z`: `aios-freelance-brain.service` намеренно остановлен владельцем; состояние `inactive`, процессов 0, unit остаётся `enabled`. Не запускать без нового решения. Журнал: `coordination/sessions/20260814-aios-arena-freelance-stop.md`.

## Главные риски

1. **✅ Дрейф текущей версии — mitigated:** `VERSION` каноничен, API/docs publication используют его цепочку, статические зеркала проверяются тестом, исторические v9/v16 документы помечены snapshot.
2. **✅ Deployment/systemd drift — mitigated:** canonical Compose закреплён; 159 installed unit names, drop-ins, masks и host overrides представлены; strict runtime drift 0, применение units остаётся отдельной operator-approved операцией.
3. **🟡 Крупные модули — controlled:** quant engine уменьшен до 1 898 строк; budgets блокируют рост dashboard/accounts/account-control/quant, следующий seam описан в `docs/MODULE_DECOMPOSITION_PLAN.md`. Остальные монолиты декомпозируются только по одному seam.
4. **✅ Dependency drift — mitigated:** роли minimal 12 / full direct 47 / exact lock 198 формализованы и проверяются; конфликт WebSockets/Web3 устранён, production lock воспроизводим на Python 3.11.
5. **✅ Tracking/ignore risk — mitigated:** глобальный `*.json` удалён, source build-каталог возвращён в Git, runtime/sensitive paths игнорируются точечно и проверяются тестом.
6. **✅ Устаревающие repository metrics — mitigated:** текущие цифры генерируются в `docs/PROJECT_INVENTORY.md`, CI проверяет exact snapshot; старые audit-документы помечены historical.
7. **✅ Негерметичный test baseline — mitigated:** live LLM/runtime paths заменены mocks/tmp fixtures; полный suite 5 160 = 5 153 passed, 7 skipped, 0 failed.
8. **✅ Runtime/generated artifacts — mitigated:** logs, CatBoost event и debug capture больше не tracked; физические production files сохранены и игнорируются точечно.
9. **✅ LLM proxy/Kilo unfinished work — completed:** 36-model catalog, tool routing/SSE, Colab guards и atomic sync покрыты тестами и развернуты; runtime healthy.

## Следующий рекомендуемый шаг

1. Следующий architecture seam: `tg_bot/accounts.py` context/router + analytics handler с сохранением порядка matching.
2. Затем Gmail/Google adapter seam в `run_account_control.py` и pure render seam в dashboard.
3. Любое применение versioned systemd units выполняется отдельно с operator approval; массовые restart/disable/remove запрещены.

## Правило обновления этого файла

Обновлять только после значимой завершённой задачи, смены общего приоритета или подтверждённого изменения runtime. Не превращать файл в подробный лог: детали принадлежат отдельным журналам `coordination/sessions/`.
