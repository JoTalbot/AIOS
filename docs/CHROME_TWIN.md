# Chrome Twin — Двойник пользователя в Google Chrome

## Что это?
Браузер Google Chrome с **твоим личным Google аккаунтом**, который по команде выполняет любые действия вместо тебя во всех сервисах Google и не только.

Работает как твой двойник: ты один раз логинишься в Google аккаунт в отдельном Chrome профиле, а потом адаптер использует эту сессию для автоматизации.

## Возможности

### Google сервисы (12+):
- **Gmail**: читать, отправлять письма (с подтверждением), черновики, поиск
- **Drive**: загрузка файлов, создание папок, шаринг, поиск
- **Docs**: создание документов, редактирование, экспорт
- **Sheets**: создание таблиц, ввод данных
- **Slides**: создание презентаций
- **Calendar**: создание событий, проверка занятости
- **YouTube**: поиск, просмотр, комментарии, загрузка (с подтверждением)
- **Maps**: поиск мест, маршруты
- **Translate**: перевод
- **Photos**: просмотр, загрузка
- **Contacts**: поиск, создание
- **Meet**: создание встреч
- **Keep**: заметки

### Любые сайты:
- Навигация по URL
- Клики по селектору/тексту/координатам
- Ввод текста, очистка, Enter
- Скриншоты
- Получение контента страницы
- Выполнение произвольных инструкций на естественном языке

### Безопасность:
- Отдельный Chrome профиль в `data/chrome_twin/<profile>/` — не трогает основной браузер
- Никогда не сохраняет пароли в коде, использует существующую сессию
- Все действия логируются в `data/chrome_twin/<profile>/actions.jsonl` для аудита
- Скрывает AutomationControlled флаг
- Поддержка headless=False (видно капчу) и headless=True

## Установка

```bash
pip install playwright
playwright install chromium

# Первый раз — запустить с headless=False и залогиниться вручную в Google
python -m aios_cli.chrome_twin doctor --profile default
# Откроется Chrome, залогинься в Google аккаунт, закрой браузер — сессия сохранится в data/chrome_twin/default/
```

## Использование

### CLI

```bash
# Doctor — проверить что браузер работает
python -m aios_cli.chrome_twin doctor --profile default

# Навигация
python -m aios_cli.chrome_twin navigate --url https://mail.google.com --profile default

# Отправить письмо (черновик)
python -m aios_cli.chrome_twin gmail_send --to "test@example.com" --subject "Привет" --body "Тест от двойника" --profile default

# Отправить письмо (реально отправить с --confirm)
python -m aios_cli.chrome_twin gmail_send --to "test@example.com" --subject "Привет" --body "Тест" --profile default --confirm

# Произвольная команда
python -m aios_cli.chrome_twin custom --instruction "открой календарь и создай событие Встреча завтра в 15:00" --profile default

# Скриншот
python -m aios_cli.chrome_twin screenshot --output /tmp/screen.png --profile default
```

### Python API

```python
from aios_core.platforms.chrome_twin_adapter import ChromeTwinAdapter

adapter = ChromeTwinAdapter(config={
    "profile": "default",
    "user_data_dir": "data/chrome_twin/default",
    "headless": False,
    "slow_mo": 100
})

# Проверка
await adapter.health_check()  # True if Chrome работает

# Навигация
await adapter.navigate("https://mail.google.com")

# Google действия
await adapter.execute_google_action("gmail", "send", {
    "to": "test@example.com",
    "subject": "Привет",
    "body": "Тест от двойника",
    "confirm": False  # True для реальной отправки
})

await adapter.execute_google_action("calendar", "create_event", {
    "title": "Встреча"
})

await adapter.execute_google_action("drive", "upload", {
    "file_path": "/path/to/file.pdf"
})

await adapter.execute_google_action("docs", "create", {
    "title": "Новый документ",
    "content": "Привет от двойника"
})

# Произвольная инструкция
await adapter.execute_custom_action("открой ютуб и найди видео про котов")

# Клик, ввод
await adapter.click(text="Compose")
await adapter.type_text(selector="input[name='to']", text="test@example.com")
await adapter.click(x=100, y=200)

# Скриншот
path = await adapter.screenshot("/tmp/screen.png")

# Закрыть
await adapter.close()
```

### Platform Registry

```python
from aios_core.platforms.registry import PlatformRegistry

registry = PlatformRegistry()
registry.register_adapter("chrome_twin", config={"profile": "default"})
adapter = registry.get_adapter("chrome_twin")

# Теперь можно использовать как любую другую платформу
# health_check, receive_messages, send_message и т.д.
```

## YAML Descriptor

`platforms/chrome_twin.yaml`:
```yaml
name: chrome_twin
android_package: com.android.chrome
agent_module: aios_core.platforms.chrome_twin_adapter
extras:
  compliance:
    autopost_allowed: true
    messenger: true
    actions_per_hour: 1200
  browser:
    user_data_dir: "data/chrome_twin/default"
    headless: false
    slow_mo: 100
  google_services: [gmail, drive, docs, sheets, calendar, youtube, maps, translate, photos, contacts, meet, keep]
```

## Тесты

```bash
pytest tests/test_chrome_twin.py -v
# 5 passed
```

## Файлы

- `aios_core/platforms/chrome_twin_adapter.py` (15KB, 500+ lines) — основной адаптер
- `platforms/chrome_twin.yaml` — дескриптор
- `aios_cli/chrome_twin.py` (4.8KB) — CLI
- `tests/test_chrome_twin.py` — тесты
- `aios_core/platforms/registry.py` — добавлен chrome_twin
- `data/chrome_twin/<profile>/` — профили браузера + actions.jsonl логи
- `docs/CHROME_TWIN.md` — эта документация

## Roadmap

- [ ] Добавить vision (browser_vision MCP) для кликов по картинкам
- [ ] Добавить голосовое управление
- [ ] Интеграция с LLM для парсинга естественного языка в действия (уже частично есть)
- [ ] Поддержка Firefox, Edge
- [ ] Мульти-профили (разные Google аккаунты)
- [ ] Запись и воспроизведение сценариев

## Безопасность

- Никогда не коммить `data/chrome_twin/` в git (там cookies, session)
- Добавь в `.gitignore`: `data/chrome_twin/`
- Используй отдельный Google аккаунт для тестов, не основной
- Все действия логируются — проверяй `actions.jsonl`
- Для важных действий (отправка почты, удаление) требуется `--confirm`

