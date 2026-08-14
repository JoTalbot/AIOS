<!-- AIOS — инструкции для ИИ-агентов и контрибьюторов -->
# AGENTS.md

Этот файл — «конституция» репозитория. Его читают: автокодер v3 (планировщик и генератор),
любые внешние кодинг-агенты (Copilot / Cursor / Cline / Codex — стандарт AGENTS.md).
Соблюдение обязательно. Ответственный: @JoTalbot.

## Параллельная и межмашинная работа (ОБЯЗАТЕЛЬНО)

Этот репозиторий изменяется людьми и разными ИИ-агентами с нескольких машин, иногда параллельно.
Неизвестные незакоммиченные изменения всегда считать чужой активной работой: не сбрасывать,
не прятать в stash, не удалять и не включать в свой коммит.

Перед любой задачей обязательно:

1. Прочитать `coordination/PROJECT_CONTEXT.md` и `coordination/README.md`.
2. Проверить `git status --short`, текущую ветку, свежие коммиты и `coordination/claims/`.
3. Создать отдельный журнал по `coordination/SESSION_TEMPLATE.md`; один файл = одна сессия/агент.
4. Для изменения кода создать собственный advisory-claim с ожидаемыми путями.
5. На паузе/завершении записать в журнал: последний результат, изменённые файлы, проверки,
   commit/незакоммиченный diff, блокеры и один конкретный следующий шаг.

Запрещено в общем или грязном worktree: `git reset --hard`, `git clean -fd`, массовый
`checkout/restore`, `git add -A`, `git commit -a`. Добавлять в индекс только собственные пути.
Параллельные агенты на одной машине используют отдельные clone/worktree. Claim не является
блокировкой и виден другим машинам только после публикации через общий Git remote.
Полный протокол и аварийный handoff: `coordination/README.md`.

## Формат общения с оператором (ОБЯЗАТЕЛЬНО)

Чтобы не перегружать окно чата и контекст:

1. Перед группой tool/команд — одно короткое сообщение: что сейчас будет сделано и зачем.
2. Во время долгой работы — только краткий статус на существенном рубеже, без потока сырых логов.
3. После группы команд — краткий результат: успех/ошибка, ключевая метрика и следующий шаг.
4. Не дублировать служебный индикатор запуска инструмента, если интерфейс показывает его сам.
5. Полные логи, diff и отчёты сохранять в session-файл/артефакт; в чат выводить только нужный итог.
6. При ошибке сообщать краткую причину и план исправления; секреты и чувствительные значения не выводить.

Исключение: полный вывод показывается по прямому запросу оператора или когда без конкретного фрагмента
невозможно безопасно принять решение.

## Золотые правила (нарушение = откат изменения)

1. Минимальные правки. Никаких полных переписываний существующих файлов.
2. Существующий файл → ТОЛЬКО diff-режим (SEARCH/REPLACE-блоки). Формат — в коде
   `aios_core/autocoder_v3.py`, это единственный принимаемый контракт.
3. Один коммит = одна задача. Ветки `auto/v3/*`, префикс коммита `auto(v3): [file]`.
4. Никогда не коммитить секреты: `.env*`, `data/.llm_keys.json`, `*secret*`, `*token*`.
5. Никаких массовых удалений: >3 удалённых файлов в изменении — подозрение на деградацию.
6. Если задача требует правки protected-файла из списка ниже — НЕ выполнять её,
   пропустить (`skip_reason=protected`) и зафиксировать в памяти.

### Protected-файлы (запрещены к изменению автокодером)

```
run_coder_orchestrator*.py   run_telegram_bot.py        scripts/selfguard.py
aios_core/autocoder_v3*.py   aios_core/llm_balancer.py  aios_core/self_protection.py
aios_core/code_rag.py        aios_core/autocoder_memory.py
aios_core/orchestrator.py    aios_core/__init__.py
aios_core/advanced_security.py  aios_core/inter_swarm.py
octopus_core/api_v2_batch.py
.env  .env.*  data/.llm_keys.json  docker-compose*.yml / *.yaml
```

Канонический источник списка: `aios_core/self_protection.py::PROTECTED_PATTERNS`.
При рассинхроне — правь `self_protection.py` (вручную) и этот файл.

## Карта репозитория

- `aios_core/` — ядро: LLM-балансер, автокодер, оркестратор, RAG, самозащита.
- `octopus_core/` — мультиагентная логика (Octopus), API v2.
- `scripts/` — сервисные скрипты (selfguard, проверки ключей, деплой).
- `run_*.py` — точки входа systemd-сервисов (оркестратор автокодера, боты, API).
- `docker-compose.prod.yml` — прод-стек (aios-api, mcp, exporter, prometheus, grafana).
- `tools/`, `utils/` — утилиты; `tests/` — тесты (pytest).

География прод-окружения: см. `RUNBOOK_RU.md` (сервисы, таймеры, логи, инциденты).
Текущие repository metrics: `docs/PROJECT_INVENTORY.md`; не копировать его цифры вручную,
обновлять командой `python scripts/generate_project_inventory.py --write`.

## Источник production deployment

- Канонический production Compose: только корневой `docker-compose.prod.yml`.
- В production всегда указывать `docker compose -f docker-compose.prod.yml ...`; голый
  `docker compose up` запрещён, потому что выберет локальный `docker-compose.yml`.
- `docker-compose.unified.yml` — experimental UI/Swarm; вложенный
  `deploy/production/docker-compose.prod.yml` — legacy v9 reference, не запускать.
- Systemd drift проверять только read-only командой
  `python scripts/audit_deployment_sources.py --runtime`; массовое удаление units запрещено.
- Карта entrypoints и безопасный reconciliation: `deploy/DEPLOYMENT_SOURCES.md`.

## Команды

```bash
# Активация окружения (ОБЯЗАТЕЛЬНО перед любыми командами)
source /opt/aios/.venv/bin/activate

# Проверки
python -m py_compile <file>          # быстрый синтаксис
pytest tests/ -q                     # тесты
ruff check .                         # линт (ошибки блокируют)

# Автокодер
python run_coder_orchestrator_v3_1.py --once        # один цикл
python run_coder_orchestrator.py --phase plan --file <путь>   # только план
python scripts/selfguard.py --force-snapshot        # после РУЧНОЙ правки protected-файлов

# Сервисы и логи
systemctl status aios-auto-coder-v3.service aios-selfguard.service
tail -f logs/coder_v3.log logs/selfguard.log
```

## Соглашения о коде

- Python 3.11; корректные type hints и docstringи у новых публичных функций.
- Логи автокодера — по-русски с эмодзи-маркерами (✅/❌/⚠️), кратко.
- Коммиты: осмысленное сообщение; для автокодера — `auto(v3): [file] desc`.
- Новые зависимости — только через requirements и обоснование в коммите.

## Версии и релизы

- Каноническая версия основного продукта хранится только в корневом `VERSION`.
- `pyproject.toml::project.version` и `aios_core.__version__` — обязательные зеркала,
  проверяемые `tests/test_release_version.py`; нельзя менять только одно из них.
- FastAPI и публикация документации обязаны получать версию из канонической цепочки,
  без собственных строковых литералов.
- Версии SDK, API-протоколов и отдельных service rollout могут иметь отдельный lifecycle.
- Полная политика и release checklist: `docs/RELEASE_VERSION_POLICY.md`.

## Контракт зависимостей

- `pyproject.toml` — minimal install metadata; `requirements.txt` — full production direct input;
  `requirements.lock` — единственный exact production lock для Docker.
- Инвариант: minimal ⊆ direct ⊆ lock, constraints обязаны удовлетворяться locked versions.
- Перед коммитом dependency changes запускать
  `python scripts/check_dependency_contract.py --strict`.
- Не использовать `pip freeze` для production lock и не делать массовый `--upgrade` заодно.
- Политика и воспроизводимая команда: `docs/DEPENDENCY_POLICY.md`.

## Тестирование

- Минимум: `py_compile` каждого изменённого файла (встроено в pipeline).
- Логические правки → добавляй/обновляй тест в `tests/` и прогоняй `pytest tests/ -q`.
- Деградация (укорочение модуля, потеря функций/классов) эквивалентна провалу тестов.

## Границы для автокодера

- Цель цикла — малое улучшение: docstringи, типы, читаемость, микро-тесты, мелкий рефакторинг.
- Не «улучшать» файлы, которые уже размечены `docs:` в памяти, — бери следующую задачу.
- Не гоняться за количеством: 1 качественный коммит лучше 5 косметических PR.
- Неизвестность ≠ повод переписать. Сомневаешься — оставь как есть, запиши в notepad.

## Workflow (канонический)

Ветка `auto/v3/<file>-<ts>` → коммит → PR → auto-promote → `main`.
Ручные правки protected-файлов: коммит + `selfguard --force-snapshot` обязательно.

## Фирменный стиль фото склада: «Авторазборка» (ОБЯЗАТЕЛЬНО для всех агентов)

Все агенты генерации контента, парсинга, OLX-пайплайна, ботов и каталога ОБЯЗАНЫ соблюдать **фирменный стиль фотографий товаров**:
1. **Сеттинг:** Реальный склад / авторазборка (`Авторазборка`).
2. **Композиция:** Детали лежат на деревянных дощатых полках или паллетах на металлическом стеллаже склада.
3. **Фон:** Складские стеллажи с автодеталями, мягкое цеховое освещение с глубиной резкости (bokeh).
4. **Характер деталей:** Реалистичные б/у запчасти с естественной текстурой металла (без 3D-графики, мультяшности и белых изолятов).
5. **Категории и база:** 10 базовых категорий (`data/photos/cat1_podveska.jpg` .. `cat10_fasteners.jpg`) и предметные фото (`data/photos/brand_item_*.jpg`).
Полный стандарт и промпты: `docs/BRAND_STYLE.md`.
