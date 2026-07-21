# AIOS v9.0.0-alpha.13 — Instagram полностью: сбор, детали, Direct, doctor

**Дата:** 2026-07-21 · **Тесты:** 811 passing (+22)

Instagram получает весь функционал уровня OLX-агента — на общих
hints-driven механиках платформ (ни одной OLX-специфичной развилки):
сбор карточек, детальный экран, guarded-переписка в Direct, драйв
поиска и doctor-отчёт.

## Что нового

### Instagram — полный функционал (`aios_core/modules/instagram/`)

- **`InstagramCollector`** — сбор карточек ленты/выдачи: движок
  OLXCollector (дамп → парсер → свайп → дедупликация), навигация через
  инъецируемый драйв (login/point), парсер резолвится из
  `extras.parser_hints` дескриптора; `collect_to_storage` пишет в
  `InstagramStorage` (история цен, неактивные, подписки).
- **`InstagramDetailParser`** — открытый пост: цена/продавец/CTA/
  описание из секции hints-detail; без калибровки — shape-режим.
- **`InstagramMessenger`** — guarded Direct **без изменений guarded-
  контура OLX**: ответ по умолчанию только в outbox-очередь
  (`dm-send`), реальная отправка — после одобрения (`dm-flush`) или
  явного `--auto-send`; Direct-inbox deep link, чтение чатов с
  маркерами калибровки, alignment-парсер диалога.
- **`InstagramBootstrap.doctor()`** — готовность: adb-бинарь,
  env-секреты (только факт наличия!), дескриптор, маркеры, хранилище,
  serial онлайн.
- **`InstagramLoginDriver`** — теперь с `search_drive`: после стены
  входа выполняет PointDrive-поиск.

### Hints-runtime (без codegen-файлов)

`platforms/runtime_hints.py`: `HintDetailParser`, `HintSender` (тап
инпута → ADBKeyBoard → тап send-маркера/ENTER, отчёт по шагам),
`detail_parser_for` / `chat_list_parser_for` / `load_hints_section` —
экраны detail и messenger собираются прямо из дескриптора любой
платформы. OLX `ChatListParser` теперь принимает маркеры параметром
(обратная совместимость сохранена).

### PointDrive — точечный поисковый драйв

Находит поисковый инпут в дампе (EditText/search-rid по bounds, без
координатных констант), вводит запрос (Cyrillic-safe) и ENTER → дамп
поисковой выдачи. Работает и как bootup-драйв.

### CLI `aios instagram`

```bash
aios instagram doctor [--serial E]
aios instagram collect --query "кросівки" --db data/instagram.sqlite [--login]
aios instagram login-drive --query "..." [--serial E]
aios instagram dm-send --chat chat:anna --text "..." [--auto-send]
aios instagram dm-outbox / dm-flush
```

### cron-plan `--with-marker-check`

Шаблонные (закомментированные) строки `platforms marker-check` по
каждой платформе каталога — drift-караул верстки приложений.

## Установка

```bash
pip install aios-9.0.0a13-py3-none-any.whl
```

## Дальше (дорожная карта к 10000+)

- AutoWatch для произвольной платформы (`aios <platform> autowatch`,
  cron-plan по каталогу).
- REST-поверхности Instagram (inbox/send) по образцу olx-модуля.
- Reels/Stories-форматы: категории контента в CalibrationAdvisor.
