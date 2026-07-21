# AIOS 9.0.0-alpha.10 — ShardGateway, health-монитор, калибровочный агент

**Дата:** 2026-07-21 · **Тесты:** 736/736 зелёные · Python ≥ 3.10

Одиннадцатый выпуск завершает контур шардинга: проксирование на хост
профиля, следящее здоровье шардов и автоматическая калибровка парсеров
новых платформ.

## Главное

### ShardGateway — REST-шлюз шардинга
- `ShardGateway.proxy(profile, method, path, ...)` — HTTP-хоп на хост
  профиля по липкому маршруту ShardRouter.
- Хост совпадает с собственным (`AIOS_HOST_ID`) → маркер `local` без
  HTTP-петли — клиент выполняет вызов локально.
- REST: `POST /api/v1/shards/gateway {profile, method, path, params?, body?}`.
- Транспорт инъецируем (тесты без сети), ошибки сети → 502 с описанием.

### ShardHealthMonitor — здоровье шардов
- Демон probe `GET <base_url>/health` по всем хостам → `set_healthy`;
  больные хосты мгновенно теряют маршруты (автомиграция ShardRouter).
- CLI: `aios shards monitor [--interval N]` или `--once` (для cron —
  встроено в cron-plan смежно с devices monitor).

### CalibrationAdvisor — калибровка парсеров
- Анализирует UI-дамп поисковой выдачи новой платформы: повторяющиеся
  контейнеры с ценой (общий `parse_price`) и заголовком → кандидатские
  resource-id маркеры карточек + статистика валют.
- `aios platforms calibrate --platform X dump.xml [--write]`
  — `--write` вливает подсказки в `extras.parser_hints` дескриптора
  `platforms/<name>.yaml` прямо в каталог.
- `PlatformDescriptor.extras` — открытое поле расширений, проброшено
  через YAML-каталог и JSON-сериализацию.

## Цифры
- 736 автотестов (+11), ~67 REST-роутов, 50+ CLI-команд.
- Роадмап PLATFORMS_SCALING закрыт целиком до крупных пунктов
  «генератор парсеров из hints» и «авто-E2E».

## Установка
```bash
pip install dist/aios-9.0.0a10-py3-none-any.whl
```
