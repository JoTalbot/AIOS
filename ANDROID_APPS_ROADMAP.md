# AIOS Android Applications Roadmap

## Current Status: v9.0.0+ (ua.slando)

### Completed
- `aios_core/android_rpa_bridge.py`: базовый Android-мост
- `aios_core/modules/olx/adb.py`: ADB-контроллер
- `aios_core/modules/olx/bootstrap.py`: bootstrap fresh-server
- `tests/test_android_rpa_bridge.py`: юнит-тесты моста
- Real-device pipeline для `ua.slando` на эмуляторе
- Замена пакета: `ua.olx.android` → `ua.slando`

---

## Milestones

### M1: Stable Real-Device Execution
**Goal:** заменить симуляцию на детерминированный UI-driven сценарий.

- Парсинг `uiautomator` XML в `search/get_item_details/send_message`
- Определение координат кликов по `resource-id`/`text`
- Стабилизация ввода кириллицы через `ADBKeyBoard`/`ime`
- Ретраи/бэкофф при падениях `uiautomator dump`

**Deliverables:**
- `aios_core/modules/olx/uiautomator_parser.py`
- Обновление `test_real_android_app.py` под парсинг реальных результатов

---

### M2: Appium Integration
**Goal:** добавить альтернативный стабильный драйвер aside from raw ADB.

- Подключение `Appium`/` UiAutomator2`
- Единый интерфейс `AndroidDriver` поверх `adb` и `appium`
- Поддержка жестов, скроллов, веб-вью
- CI-ready headless запуск

**Deliverables:**
- `aios_core/android_rpa_driver.py`
- `tests/test_android_appium_driver.py`

---

### M3: Multi-App Abstraction
**Goal:** поддержка N приложений через дескрипторный подход.

- Платформо-agnostic endpoints для search/message/details
- Регистрация приложений через `aios_core/platforms/*`
- Поддержка `com.facebook.katana`, `com.instagram.android`

**Deliverables:**
- Реестр платформ + драйверы
- Тесты мультиплатформенности

---

### M4: Device Fleet Management
**Goal:** параллельный запуск на пуле эмуляторов/устройств.

- Pool: lease/release/heartbeat
- sticky route: профиль → устройство
- Максимальное параллелизм
- Cross-emulator cleanup

**Deliverables:**
- `aios_core/platforms/device_pool.py`
- Интеграция с `aios_core/api/app.py`

---

### M5: AI-Powered UI Navigation
**Goal:** обучение скриптам действий на реальных скриншотах.

- Классификация экранов через CV/CLIP
- Обёртки для ретраев при изменении UI
- Self-healing locators

**Deliverables:**
- `aios_core/android_screen_classifier.py`
- Примеры интеграции с `multidimensional_world_model`

---

### M6: Observability & Analytics
**Goal:** полная трассировка действий на Android.

- Отправка событий в `aios_core/telemetry.py`
- Логирование каждой tap/type/swipe в JSON
- Дашборды в Web UI

---

## Execution Order
M1 → M2 → M3 → M4 → M5 → M6

## Dependencies
- Android SDK / Emulator
- ADB + ADBKeyBoard
- Appium server
- Python: `appium-python-client`, `opencv-python`, `pillow`

## Success Criteria
- 100% тестов проходят на `emulator-5554`
- Поддержка `ua.slando` + 2 других приложений
- CI job c headless-эмулятором
