# AIOS — Роадмап завершения конституции

## Версия: 1.0
## Дата: 2026-07-19
## Автор: автономный анализатор AIOS
## Основа: репозиторий `JoTalbot/AIOS` (`docs/constitution/`)

---

## Фаза 0 — Подготовка (Завершено частично)

| Задача | Статус | Ответственный |
|---|---|---|
| Клонирование репозитория AIOS | ✅ Выполнено | Агент |
| Анализ всех статей (I–LXVII) | ✅ Выполнено | Агент |
| Выявление ошибок имён (`RTICLE-`, `# ARTICLE-`) | ✅ Обнаружено | Агент |
| Создание документации AIOS | ✅ Выполнено | Анализатор |
| Создание `.gh_token` | ✅ Выполнено | Агент |

---

## Фаза 1 — Формальная корректировка (Критично, 1 день)

### 1.1. Исправление имён файлов

**Команда:**
```bash
cd /home/user/AIOS_project/repo/docs/constitution/
mv RTICLE-XLIX-EXISTENCE.md ARTICLE-XLIX-EXISTENCE.md
mv '# ARTICLE-LX-PROTOCOLS.md' ARTICLE-LX-PROTOCOLS.md
```

**Проверка:**
```bash
ls ARTICLE-XLIX-EXISTENCE.md ARTICLE-LX-PROTOCOLS.md
```

**Соответствие инструкциям:** `ARTICLE-I` (Identity must be unique), `ARTICLE-XXX-CONSTITUTIONAL-INTERPRETATION.md` (Non-Circumvention).

---

## Фаза 2 — Инструмент проверки (`tula`) (Критично, 2 дня)

### 2.1. Функциональность инструмента (`tools/complete_constitution_tula.py`)

- [x] Сканирование `docs/constitution/`
- [x] Проверка нумерации (I → LXVII)
- [x] Проверка структуры секций (Status, Level, Scope, Principle, Laws, Final Rule, END)
- [x] Генерация отчёта (`constitution_report.md`)
- [ ] Автоматическое исправление имён (опционально, с флагом `--fix`)
- [ ] Генерация шаблонов для отсутствующих статей
- [ ] Экспорт матрицы соответствия (`constitution_compliance_matrix.md`)

### 2.2. Запуск инструмента

```bash
python3 /home/user/AIOS_project/repo/tools/complete_constitution_tula.py --scan docs/constitution/ --report CONSTITUTION_REPORT.md --fix-names
```

---

## Фаза 3 — Внутренняя связность репозитория AIOS (Средний приоритет, 3 дня)

### 3.1. Новые инструкции

| Файл | Содержание |
|---|---|
| `docs/constitution/INDEX.md` | Центральный указатель статей |
| `docs/constitution/COMPLIANCE_MATRIX.md` | Матрица соответствия |

### 3.2. Правило для репозитория AIOS

> Каждый новый документ в репозитории `AIOS` должен содержать ссылку на соответствующую статью конституции. При отсутствии соответствия — необходимо исправить или дополнить документацию. 

---

## Фаза 4 — Матрица соответствия (Высокий приоритет, 4 дня)

### 4.1. Цель

Создать `docs/constitution/COMPLIANCE_MATRIX.md` — таблицу, связывающую каждую статью с конкретной реализацией в репозитории.

### 4.2. Пример записи

| Статья | Реализация в коде/документации | Статус |
|---|---|---|
| ARTICLE-I (Identity) | `docs/core/AIOS_AGENT_MODEL.md` — Agent-ID, `docs/core/AIOS_DATA_MODEL.md` — Object-ID | ✅ Реализовано |
| ARTICLE-II (Memory) | `docs/core/AIOS_MEMORY_ARCHITECTURE.md`, `docs/memory/` | ✅ Реализовано |
| ARTICLE-XXXVI (Evolution) | `docs/core/AIOS_EVOLUTION_ENGINE.md`, `docs/architecture/AIOS_EVOLUTION_PLAN.md` | ✅ Реализовано |

---

## Фаза 5 — Финализация документации (Средний приоритет, 5 дней)

### 5.1. Новые документы

| Документ | Описание |
|---|---|
| `docs/constitution/INDEX.md` | Полный указатель статей с ссылками на текст |
| `docs/constitution/COMPLIANCE_MATRIX.md` | Матрица соответствия (см. Фаза 4) |
| `docs/constitution/VERSION_HISTORY.md` | История изменений конституции (1.0 → 1.1) |
| `docs/constitution/INTERPRETATION_GUIDE.md` | Руководство по толкованию (на основе `ARTICLE-XXX`) |

### 5.2. Обновление существующих документов

- `AIOS_PROJECT_ROADMAP.md` — добавить ссылку на статус конституции.
- `AIOS_BOOTSTRAP.md` — добавить шаг «Проверить соответствие конституции».
- `AIOS_DOCUMENT_INDEX.md` — добавить раздел `constitution`.

---

## Фаза 6 — Автономная проверка (Низкий приоритет, постоянная)

### 6.1. Цикл агента

Каждый запуск инструмента `tula` (по требованию или по расписанию):

1. Запустить `complete_constitution_tula.py`.
2. Если обнаружены ошибки — создать лог в `docs/constitution/logs/` или обновить `CONSTITUTION_REPORT.md`. 
3. Если все статьи соответствуют — создать `heartbeat` отчёт.

### 6.2. Уведомление о статусе (внутренний цикл AIOS)

- Отправка краткого отчёта о статусе конституции (только при изменении статуса или ошибке).

---

## Фаза 7 — Финальная версия 2.0 (Стратегический приоритет, 30+ дней)

### 7.1. Условия для версии 2.0

- Все ошибки имён исправлены.
- Матрица соответствия заполнена на 100%.
- Есть минимум 3 успешных автономных цикла проверки без ошибок.
- Документ `INTERPRETATION_GUIDE.md` принят и проверен.

### 7.2. Изменения для 2.0

- Обновление `PREAMBLE.md` (добавление ссылки на версию 2.0).
- Добавление `ARTICLE-LXVIII` — `CONSTITUTIONAL_INTEGRITY` (если необходимо).
- Финализация `docs/constitution/VERSION_HISTORY.md`.

---

## Итоговый контрольный список

```markdown
- [ ] Фаза 1: Исправление имён файлов (2 файла)
- [ ] Фаза 2: Создание `tula` (скрипт проверки)
- [ ] Фаза 3: Внутренняя связность репозитория AIOS (новые документы)
- [ ] Фаза 4: Матрица соответствия
- [ ] Фаза 5: Новые документы (INDEX, COMPLIANCE_MATRIX, VERSION_HISTORY, INTERPRETATION_GUIDE)
- [ ] Фаза 6: Автономный цикл проверки
- [ ] Фаза 7: Подготовка версии 2.0
```

---

## Связь с репозиторием AIOS

Этот роадмап разработан для репозитория `JoTalbot/AIOS` и использует:

- Мета-инструкцию `00_README.txt`
- Языковую директиву `01_russian_only.txt`
- Документы `docs/skills/SKILL_ENGINE_ARCHITECTURE.md` 
- Документы `docs/core/AIOS_AUTONOMY_MODEL.md` 
- Документы `docs/core/AIOS_EVOLUTION_ENGINE.md`, `docs/core/AIOS_MEMORY_ARCHITECTURE.md` 
- Канонический путь `docs/constitution/` 

---

*Документ сгенерирован автономным анализатором на основе репозитория `JoTalbot/AIOS`. .**
