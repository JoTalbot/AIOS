# OLX Android Agent

## Статус
✅ OLX Parser Agent завершён (2026-07-21).

Дата: 2026-07-21

## Среда

Приложение:
- Package: ua.slando
- Version: 5.170.3
- versionCode: 8007

Устройство:
- Android через ADB
- UIAutomator inspection

## Что реализовано

### Управление приложением через ADB

Используются команды:

- запуск действий через adb shell input
- свайпы:

adb shell input swipe


- получение UI дерева:

adb shell uiautomator dump


- загрузка XML:

adb pull


## Анализ списка объявлений

Обнаружены UI элементы:


AdsListLayout
adListing_adGridCard
ad_grid_card_image


Карточка объявления содержит:

- название
- цену
- город
- дату публикации
- изображения
- статус TOP

Пример:

BMW X3 G01 (2017-) - лобове скло, стекло лобовое

Цена:
7000 грн

Город:
Львів

Дата:
Сьогодні в 11:26


## Поисковый модуль

Проверен запрос:

"лобове скло"

Результат:

МИ ЗНАЙШЛИ 1000 ОГОЛОШЕНЬ


## Полученные возможности

AIOS может:

- открыть OLX Android приложение
- выполнить поиск
- прокручивать список
- получать UI дерево
- находить карточки объявлений
- извлекать текстовые данные


## Ограничения

UI построен на Jetpack Compose.

Большая часть элементов не имеет resource-id.

Используется анализ:

- text
- bounds
- resource-id
- UI hierarchy


## Следующий этап — ВЫПОЛНЕН ✅

OLX Parser Agent реализован (`aios_core/modules/olx/`, 17 тестов):

1. ✅ автоматический сбор карточек — `OLXCollector` (скроллинг ленты
   свайпами, дедупликация по fingerprint, остановка в конце выдачи)
2. ✅ извлечение ссылок — `CardParser` поднимает URL и ad_id из атрибутов
   узлов (`https://www.olx.ua/.../IDxxxx.html`); ограничение: UIAutomator
   выдаёт ссылки только когда они присутствуют в content-desc
3. ✅ сохранение в БД AIOS — `OLXStorage` (SQLite, INSERT OR IGNORE по
   fingerprint, фильтры по запросу/городу)
4. ✅ анализ конкурентов — `CompetitorAnalyzer` (мин/макс/медиана цены,
   доля TOP, топ городов, ценовой перцентиль)
5. ✅ генерация рекомендаций для объявлений — `RecommendationEngine`
   (рекомендуемая цена = медиана рынка × 0.97, вердикт
   below_market/competitive/above_market, ключевые слова для заголовка,
   целесообразность TOP-продвижения)

### Пример использования

```python
from aios_core.modules.olx import OLXCollector, OLXStorage, RecommendationEngine

collector = OLXCollector()
collector.launch_search("лобове скло")  # deep-link в приложение OLX

with OLXStorage("olx_ads.sqlite") as storage:
    summary = collector.collect_to_storage(storage, query="лобове скло", max_cards=50)
    ads = storage.get_ads(query="лобове скло")

advice = RecommendationEngine().recommend(ads, my_ad=my_draft)
print(advice.to_text())
```

Тесты: `tests/test_olx_agent.py`.

## Планировщик и REST API (2026-07-21)

### Периодический сбор — `CollectionScheduler`

```python
from aios_core.modules.olx import CollectionScheduler, OLXStorage

with OLXStorage("olx_ads.sqlite") as storage:
    scheduler = CollectionScheduler(storage=storage, interval_s=3600)
    scheduler.start(["лобове скло", "скло бокове"], max_cards=100)
    ...
    scheduler.stop()
    print(scheduler.history)  # parsed/inserted/total по каждому запуску
```

Хранилище `OLXStorage` потокобезопасно: одно подключение обслуживает и
фоновый планировщик, и REST API.

### REST-эндпоинты

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/api/v1/modules/olx/ads` | Сохранённые объявления (фильтр `query`, `limit`) |
| GET | `/api/v1/modules/olx/stats` | Статистика рынка по запросу |
| POST | `/api/v1/modules/olx/recommendations` | Рекомендации для объявления |
| POST | `/api/v1/modules/olx/collect` | Разовый сбор через ADB |
| POST | `/api/v1/modules/olx/schedule` | Запуск периодического сбора (`interval_s >= 10`) |
| DELETE | `/api/v1/modules/olx/schedule` | Остановка периодического сбора |
| GET | `/api/v1/modules/olx/history` | История цен по `fingerprint` |
| GET | `/api/v1/modules/olx/drops` | Падения цен + ушедшие из выдачи |

Тесты: `tests/test_olx_api.py`.

## История цен и активность (2026-07-21)

Хранилище версии v2 (`olx_sightings`) записывает каждое наблюдение
объявления: цена, время, TOP. Это даёт:

- **историю цен** по каждому объявлению (`price_history`);
- **отслеживание активности**: объявление, исчезнувшее из выдачи запроса,
  помечается `is_active = 0` (вероятно, продано) и воскресает при возврате;
- **`PriceTracker.price_drops()`** — объявления с упавшей ценой
  (первая против последней фиксации);
- **экспорт** в CSV/JSON.

Идентичность объявления (`fingerprint`) больше не зависит от цены:
`ad_id` → `url` → `title|city|query`, поэтому изменение цены — это
история одного объявления, а не новое объявление.

### CLI

```bash
aios olx collect --query "лобове скло" --max-cards 50   # сбор через ADB
aios olx stats --query "лобове скло"                    # статистика рынка
aios olx recommend --query "лобове скло" --price 9000 --title "Скло BMW X3"
aios olx export --format csv --output ads.csv           # экспорт
aios olx history --fingerprint ab12cd34ef56gh78         # история цен
aios olx drops --query "лобове скло"                    # падения цен
```
