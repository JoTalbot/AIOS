# AIOS v9.0.0-alpha.14 — Generic AutoWatch + Messenger REST + категории контента

**Дата:** 2026-07-21 · **Тесты:** 823 passing (+12)

Цикл заботы AutoWatch теперь универсален для любой платформы каталога;
guarded-переписка доступна по REST всем платформам с messenger-модулем
(Instagram Direct сразу); калибровщик не теряет видео-форматы.

## Что нового

### Generic AutoWatch (`platforms/autowatch.py`)

Полный цикл OLX AutoWatch (сбор подписок → алерты → снапшот своих →
застой → предложения/repost-план) для любой платформы:

- profile-scoped хранилище и ADB через резолвер;
- парсер карточек по цепочке: codegen-модуль платформы → runtime
  hints (`resolve_card_parser`);
- опциональный драйв навигации перед каждым запросом
  (`--drive point|login`);
- CLI: `aios platforms autowatch --platform instagram --profile main
  --query "кросівки" [--webhook URL] [--no-collect]`;
- cron-plan: профили не-olx платформ получают generic-строки,
  olx — родную команду (совместимость).

### Guarded messenger REST plane

Любая платформа с `<agent_module>.messenger` (класс
`*Messenger(OLXMessenger)`) получает REST-переписку — Instagram Direct
подхватился автоматически:

- `GET /api/v1/modules/{platform}/chats?profile=…`
- `GET /api/v1/modules/{platform}/outbox[?status]`
- `POST /outbox/send {chat_key, text, auto_send?}` — **очередь по
  умолчанию**: без явного `auto_send` ничего не уходит на устройство;
- `POST /outbox/flush` — отправка одобренных; честный `failed` при
  недоступном устройстве;
- платформа без messenger-модуля → 404 с рецептом.

### Категории контента в калибровке

`CalibrationAdvisor.analyze` дополнительно возвращает
`content_categories`: video/reels-маркеры, story/highlight-маркеры,
счётчик duration-меток (`0:32`) — Reels/Stories-форматы без цены
учитываются при онбординге платформ с непродуктовой лентой.

## Установка

```bash
pip install aios-9.0.0a14-py3-none-any.whl
```

## Дальше (дорожная карта к 10000+)

- Own-posts для Instagram (guarded-публикация по образцу olx own_ads).
- Video-first экстрактор карточек (views/likes вместо цены).
- FleetScheduler: балансировка autowatch-циклов платформ по пулу
  устройств + drift-алёрты в webhook.
