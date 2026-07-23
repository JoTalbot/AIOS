# Contributing to AIOS

Спасибо за интерес к проекту AIOS! 🎉

## Как внести вклад

### 1. Fork и клонирование

```bash
git clone https://github.com/YOUR_USERNAME/AIOS.git
cd AIOS
git remote add upstream https://github.com/JoTalbot/AIOS.git
```

### 2. Создание ветки

```bash
git checkout -b feature/your-feature-name
# или
git checkout -b fix/bug-description
# или
git checkout -b docs/documentation-improvement
```

### 3. Разработка

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск тестов
python -m pytest -q

# Проверка кода
black aios_core/
flake8 aios_core/
```

### 4. Коммиты

Используйте conventional commits:

```
feat: add new platform scaffold
fix: correct compliance guard logic
docs: update production guide
test: add tests for AI advisor
refactor: simplify orchestrator
chore: update dependencies
```

### 5. Pull Request

```bash
git push origin feature/your-feature-name
```

Откройте PR на GitHub. Опишите:
- Что изменено
- Почему
- Как тестировалось
- Скриншоты (если применимо)

---

## Стандарты кода

### Python

- **Форматирование:** Black (line length 100)
- **Импорты:** сгруппированы, отсортированы
- **Типы:** type hints для публичных функций
- **Документация:** docstrings для всех классов и публичных методов
- **Тесты:** pytest, минимальное покрытие 80% для нового кода

### Структура

```
aios_core/
├── modules/
│   └── <platform>/        # Один модуль на платформу
│       ├── __init__.py
│       ├── collector.py
│       ├── detail.py
│       └── ...
├── <feature>.py           # Один файл на фичу
└── tests/
    └── test_<feature>.py  # Тесты рядом с кодом
```

### Платформы

При добавлении новой платформы:

1. Создайте YAML-дескриптор в `platforms/<platform>.yaml`
2. Создайте модуль в `aios_core/modules/<platform>/`
3. Используйте `platforms/scaffold.py` для генерации шаблона
4. Добавьте compliance-флаги
5. Напишите тесты
6. Обновите документацию

### Документация

- **MkDocs:** редактируйте markdown в `docs/`
- **Sphinx:** обновляйте `docs/source/*.rst`
- Локальная проверка: `mkdocs serve`
- Все новые страницы должны быть добавлены в `mkdocs.yml` → `nav`

---

## Тестирование

```bash
# Все тесты
python -m pytest -q

# Конкретный модуль
python -m pytest tests/test_ai_advisor.py -v

# С покрытием
python -m pytest --cov=aios_core --cov-report=html

# Без real device
python -m pytest -q -k "not real_device"
```

### Написание тестов

```python
import pytest
from aios_core.your_module import YourClass

class TestYourClass:
    def test_basic_functionality(self):
        obj = YourClass()
        result = obj.do_something()
        assert result is not None

    def test_edge_case(self):
        obj = YourClass(config={})
        with pytest.raises(ValueError):
            obj.do_something(invalid=True)

    @pytest.mark.asyncio
    async def test_async_method(self):
        obj = YourClass()
        result = await obj.async_method()
        assert result["status"] == "ok"
```

---

## CI/CD

Проект использует GitHub Actions:

- **CI** (`ci.yml`) — тесты на Python 3.11, 3.12, 3.13
- **Docs** (`docs.yml`) — деплой MkDocs на GitHub Pages
- **Release** (`release.yml`) — создание release при tag
- **Android** (`android.yml`) — Android-тесты

Все PR должны проходить CI перед merge.

---

## Общение

- **Issues:** используйте GitHub Issues для багов и feature requests
- **Security:** см. [SECURITY.md](SECURITY.md) для отчётов об уязвимостях
- **Вопросы:** jo.talbot@gmail.com

---

## Процесс Code Review

1. **Автор** открывает PR с заполненным шаблоном
2. **CI** должен быть зелёным (тесты + quality checks + typecheck)
3. **Ревьюер** проверяет:
   - Соответствие конституционным статьям (compliance)
   - Стиль кода (Black, isort)
   - Наличие тестов для новой функциональности
   - Отсутствие `print()` вместо `logging` в библиотечном коде
   - Отсутствие bare `except:` (использовать `except Exception:`)
   - Наличие docstrings для публичных функций
4. **Squash & merge** после аппрува

---

## Процесс релиза

1. Обновить версию в `pyproject.toml` и `aios_core/__init__.py`
2. Обновить `CHANGELOG.md` через `release-drafter`
3. Создать аннотированный тег: `git tag -a v9.4.0 -m "Release 9.4.0"`
4. Запушить тег: `git push origin v9.4.0`
5. CI автоматически соберёт и опубликует релиз

---

## Лицензия

Внося код, вы соглашаетесь с тем, что ваш вклад будет лицензирован под условиями проекта.
