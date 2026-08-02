# Instagram Emulator Adapter

## Overview
Новый адаптер `instagram_emulator` для работы с Instagram через Android эмулятор (ADB/UIAutomator), в отличие от существующего `instagram` который использует Meta Graph API.

## Архитектура
- **Package**: `com.instagram.android`
- **Storage**: `InstagramStorage` (наследник OLXStorage, SQLite per profile)
- **ADB**: `ADBController` с serial привязкой профиля
- **Messenger**: `InstagramMessenger` (guarded outbox, approval-only)
- **Collector**: `InstagramCollector` + `ReelsCollector` для ленты и Reels
- **Login**: `InstagramLoginDriver` с env секретами `AIOS_SECRET__INSTAGRAM__USERNAME/PASSWORD`
- **RPA**: `AndroidRPADeviceEmulator` для UI автоматизации

## Отличия от Graph API адаптера
| | instagram (Graph API) | instagram_emulator (ADB) |
|---|---|---|
| Требует | Business Account, Graph API token | Эмулятор с установленным Instagram APK |
| Сообщения | Webhook + Graph API | UI Automator, парсинг экрана |
| Посты | Graph API /media | PostComposer через UI |
| Лента | Graph API | ReelsCollector + InstagramCollector |
| Логин | OAuth token | ADB Keyboard + env secrets |
| Compliance | ToS разрешает с токеном | Read-only по умолчанию, постинг с --confirm |

## Использование

### Doctor check
```bash
aios platforms instagram_emulator doctor --serial emulator-5554 --profile main
# или
python -m aios_cli.instagram_emulator doctor --serial emulator-5554
```

### Login
```bash
export AIOS_SECRET__INSTAGRAM__USERNAME='your_email'
export AIOS_SECRET__INSTAGRAM__PASSWORD='your_pass'
python -m aios_cli.instagram_emulator login --serial emulator-5554 --profile main
```

### Collect feed
```bash
python -m aios_cli.instagram_emulator collect --serial emulator-5554 --max 50 --query "sneakers"
```

### Collect Reels
```bash
python -m aios_cli.instagram_emulator reels --serial emulator-5554 --max 50
```

### Send Direct message
```bash
# Outbox (requires approval)
python -m aios_cli.instagram_emulator send --serial emulator-5554 --recipient user123 --text "Hello"

# Auto-send with --confirm (on your risk)
python -m aios_cli.instagram_emulator send --serial emulator-5554 --recipient user123 --text "Hello" --confirm
```

### Create post
```bash
python -m aios_cli.instagram_emulator post --serial emulator-5554 --caption "My post #test" --image /path/to/image.jpg
```

## Код

### Platform Registry
```python
from aios_core.platforms.registry import PlatformRegistry
registry = PlatformRegistry()
registry.register_adapter("instagram_emulator", config={"serial": "emulator-5554", "profile": "main"})
adapter = registry.get_adapter("instagram_emulator")
await adapter.health_check()  # Check emulator + Instagram installed
await adapter.collect_feed(max_cards=50)
await adapter.send_message("user123", "Hello", metadata={"auto_send": False})
```

### Emulator Components
- `ADBController`: `adb devices`, `pm list packages`, `dump_ui`, `swipe`, `input_text`
- `InstagramMessenger`: `open_chats()`, `list_chats()`, `read_chat()`, `_type_and_send()`
- `InstagramCollector`: `collect(max_cards, query)` -> list[VideoCard]
- `ReelsCollector`: `collect(max_cards)` -> Reels
- `PostComposer`: `compose_text_post(caption)`, `compose_with_image(caption, image_path)`

## YAML Descriptor
`platforms/instagram_emulator.yaml`:
```yaml
name: instagram_emulator
android_package: com.instagram.android
agent_module: aios_core.modules.instagram
storage_class: aios_core.modules.instagram.storage.InstagramStorage
adb_class: aios_core.modules.olx.adb.ADBController
extras:
  compliance:
    autopost_allowed: true
    messenger: approval-only
    collector: true
    actions_per_hour: 60
```

## Тесты
```bash
pytest tests/test_instagram_emulator.py -v
# 5 PASSED
```

## Compliance
- Instagram ToS запрещает автоматизацию — сбор read-only по умолчанию
- Direct через approval-outbox
- Постинг только с явным --confirm (на свой риск)
- Действия лимитированы 60/час (compliance)

## Files
- `aios_core/platforms/instagram_emulator_adapter.py` (13KB, 298 lines)
- `platforms/instagram_emulator.yaml`
- `aios_cli/instagram_emulator.py` (4.8KB CLI)
- `aios_core/platforms/registry.py` (added emulator)
- `tests/test_instagram_emulator.py` (5 tests)

## Future
- Добавить Stories collection
- Добавить Profile parser (followers, bio)
- Добавить Comment automation
- Интеграция с DevicePool и FleetScheduler для множества эмуляторов
