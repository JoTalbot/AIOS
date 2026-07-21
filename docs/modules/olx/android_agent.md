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

## Детальна сторінка, переписка, свої оголошення (2026-07-21)

### Парсинг сторінки оголошення — `AdDetailParser`
Ціна, параметри (`Стан`, доставка), опис, продавець (ім'я/тип/на OLX з),
місто, лічильник переглядів, дата публікації. REST: `POST /olx/detail`.

### Особисті чати — `OLXMessenger`
- `ChatListParser`: перелік чатів (співрозмовник, оголошення, сніпет,
  непрочитані, координати тапу).
- `ChatViewParser`: напрямок повідомлень за стороною екрана.
- `ReplySuggester`: чернетки відповідей (актуальність, торг з мін. порогом,
  зустріч, привітання).
- **Захист**: відповідь спочатку падає в `olx_outbox`; на пристрій уходить
  тільки з `auto_send=True` або явним флашем (`POST /olx/outbox/send`).
- REST: `GET /olx/chats`, `POST /olx/chats/reply`, `GET /olx/outbox`,
  `POST /olx/outbox/send`, `POST /olx/outbox/cancel`.
- Кирилиця на реальному пристрої потребує ADBKeyBoard-IME.

### Контроль своїх оголошень — `OwnAdsTracker`
Парсер «Мої оголошення» (перегляди/обрані/повідомлення/статус), снапшоти
з дельтами лічильників, `stagnant()` — застояні оголошення.
REST: `GET/POST /olx/own*`.

### Покращення і перевикладання — `promotion.py`
- `AdImprover`: ключові слова в заголовок, ціна проти медіани, доповнення опису.
- `RepostPlanner`: рішення про перевикладання (вік ≥ 3 дн., < 1 перегляду/день,
  пікові години 18:00–21:00).
- `Reposter`: **DRY-RUN за замовчуванням**, виконання тільки з `confirm=True`.
  ⚠️ Перевикладання може суперечити правилам OLX щодо дублів — первинне
  призначення модуля: рекомендації + ручне підтвердження.

### Сповіщення — `notifier.py`
Вебхуки (Slack/Discord/Telegram Bot API): падіння цін конкурентів і застій
своїх оголошень. REST: `POST /olx/notify `.

### MCP
`olx_market_stats`, `olx_listing_recommend`, `olx_price_drops`
(тільки читання, через ConstitutionGuard).

## Профіль, конкуренти, радник, бутстрап (2026-07-21)

### Профіль і налаштування
`ProfileParser` читає поля профілю (ім'я, телефон, місто, про себе) та
перемикачі налаштувань; `ProfileEditor` готує зміни (dry-run → `_pending_*`
у kv-сховищі, пристрій тільки з `confirm=True`).

### Стеження за конкурентами — від своїх оголошень
`CompetitiveWatch` виводить пошуковий запит із заголовка свого оголошення,
зв'язує схожі ринкові оголошення (`olx_competitor_links`, оцінка
Jaccard+ціна+місто), рахує дешевших конкурентів і цінову позицію
(ранг серед подібних).

### Радник стратегії
- `advise_actions()`: KEEP / EDIT_PRICE / EDIT_CONTENT / REPOST / PROMOTE з
  пріоритетами й поясненнями по кожному своєму оголошенню.
- `advise_new_listings()`: активні ніші без покриття портфоліо — цільова ціна
  й стартовий заголовок із ринкових ключових слів.
- REST: `GET /olx/advisor` (`?new=1`).

### Бутстрап свіжого сервера
`aios olx bootstrap` — друкує повний план (apt → Python deps →
platform-tools → ADBKeyBoard → SDK → образ Android 34 → headless AVD
`aios-olx` → налаштування пристрою); `--execute` — виконує. Обгортка:
`tools/olx_bootstrap.sh`. Перевірка готовності: `aios olx doctor` або
`GET /olx/doctor` — чекліст із підказками виправлення.

## Обхід портфеля конкурента (2026-07-21)

На сторінці оголошення OLX показує блок «Інші оголошення користувача» —
усього портфеля продавця. `parse_seller_ads()` розбирає цей блок з
UI-дампа (захисти: наявність заголовка блока + виключення переглянутого
оголошення за URL/ad-id), а `CompetitiveWatch.observe_seller_ads()`:

1. зберігає всі картки конкурента як ринкові спостереження (історія цін
   працює і для них);
2. зв'язує з моїм оголошенням лише достатньо схожі (поріг link_score) —
   «сусідній» товар того ж продавця не змішується з прямими конкурентами;
3. повторне сканування тієї самої сторінки не створює дублікатів.

- REST: `POST /api/v1/modules/olx/competitive/seller-scan`
  `{fingerprint, xml, viewed_url?, viewed_ad_id?}`.
- CLI: `aios olx competitive-seller dump.xml --fingerprint <fp>
  [--viewed-ad-id z7kLq]`.

## Мультипрофільність: платформи й акаунти (2026-07-21)

Архітектура «платформа → профілі» (`aios_core/platforms/`): реєстр
дескрипторів платформ + реєстр профілів-акаунтів. Кожен профіль
(`olx:work`) має ізольоване сховище `data/olx/<profile>.sqlite` і
прив'язку до пристрою (`device_serial` → `adb -s <serial>`, паралельна
робота емуляторів). Розв'язання профілю: `--profile`/`?profile=` →
`AIOS_PROFILE` → default реєстру → вбудований legacy `default`
(`olx_ads.sqlite`, повна зворотна сумісність).

- CLI: `aios platforms`, `aios profiles list|add|show|remove|set-default`,
  усі olx-команди з `--profile`; явний `--db` обходить реєстр.
- REST: `/api/v1/platforms`, `/api/v1/profiles*`, будь-який модульний маршрут
  з `?profile=<name>`; невідомий профіль → 400.
- Масштабування на 10000+ застосунків: docs/PLATFORMS_SCALING.md.

## Scaffold, Fleet, PoolMonitor (2026-07-21)

`aios platforms scaffold --name X --package ua.x.app` генерує скелет нової
платформи (YAML-дескриптор + модуль зі storage-нащадком OLXStorage +
smoke-тест). `ensure_device()` (CLI `aios devices ensure --profile
olx:work`) гарантує профілю пристрій: аренда з пулу, а за нестачі —
створення AVD, запуск headless-емулятора й реєстрація в пулі.
`PoolMonitor` (CLI `aios devices monitor`) — демон heartbeats:
`adb devices` → heartbeat + reap мовчазних у offline.
