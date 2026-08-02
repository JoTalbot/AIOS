<!-- AIOS — инструкции для ИИ-агентов и контрибьюторов -->
# AGENTS.md

Этот файл — «конституция» репозитория. Его читают: автокодер v3 (планировщик и генератор),
любые внешние кодинг-агенты (Copilot / Cursor / Cline / Codex — стандарт AGENTS.md).
Соблюдение обязательно. Ответственный: @JoTalbot.

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
