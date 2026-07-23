# Руководство пользователя M7 - Android AI Navigation

## Основные функции

### AI-ориентированные локаторы (Self-Healing Locators)
Автоматически адаптируются к изменениям в интерфейсе приложений:
```python
from aios_core.android_ai_navigation import SelfHealingLocator

locator = SelfHealingLocator(driver)
success = locator.tap_hint(["login_button", "Sign In", "Войти"])
```

### Эмербеддинги экранов для сравнения
Мгновенное распознавание состояний экрана:
```python
from aios_core.android_ai_navigation import AIScreenClassifier

classifier = AIScreenClassifier()
result = classifier.classify(ui_automator_xml)
print(f"Screen: {result.name}, Confidence: {result.score:.2f}")
```

### Предиктивное позиционирование элементов
Оптимальное расположение кликов:
```python
position = classifier.predict_element_position(element)
x, y = position
driver.tap(x, y)
```

### Автоматическая генерация тест-кейсов
Генерация тестов из пользовательских сценариев:
```bash
./aios_core/android_registry.py "smart_login" "mart" "commerce"
```

## Примеры использования

### Работа с несколькими приложениями
```python
from aios_core.android_fleet import DeviceFleet

fleet = DeviceFleet()
device = fleet.acquire()
driver = device.get_driver("ua.slando")
```

### Мониторинг с M7-эвристиками
```python
from aios_core.android_observability import AndroidObservability

obs = AndroidObservability("emulator-5554")
obs.isolate_process()
risk = obs.predict_failure_risk()
```

## Методы классификации

| Метод | Описание | Возвращаемое значение |
|-------|----------|----------------------|
| `classify()` | Классификация экрана по эмербеддингу | `ScreenEmbedding` |
| `predict_element_position()` | Прогноз оптимальной позиции | `(x, y)` |
| `check_heuristic_anomalies()` | Проверка аномалий системы | `List[Dict]` |

## Миграция с M5/M6

Все функции обратной совместимости сохранены. Новые методы доступны через:
```python
from aios_core.android_ai_navigation import AIScreenClassifier
```
