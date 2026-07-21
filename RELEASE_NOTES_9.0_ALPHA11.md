# AIOS v9.0.0-alpha.11 — ParserGen + Bootup E2E: платформа «из APK до коллектора»

**Дата:** 2026-07-21 · **Тесты:** 760 passing (+24)

Цикл подключения новой платформы к AIOS собран полностью: от чужого APK
до работающего парсера карточек — одной командой, без ручного кода.

## Что нового

### ParserGen — компиляция парсера из parser_hints
`aios_core/platforms/parsergen.py` замыкает петлю «калибровка → парсер»:

- `extract_markers(hints)` — `com.demo:id/adCard` → `adcard`
  (substring-матч, lowercase, дедупликация);
- `build_parser(hints)` — runtime-парсер прямо из словаря подсказок
  (без файлов — для verify-шагов и REST);
- `write_parser(name, hints, overwrite=False)` — codegen
  `aios_core/modules/<module>/card_parser.py`: подкласс OLX CardParser
  с маркерами платформы + идемпотентный импорт в `__init__.py`;
- `parser_for(name)` — парсер прямо из YAML-дескриптора каталога:
  коллектор работает сразу после `calibrate --write`;
- CLI: `aios platforms codegen --platform X [--dry-run] [--force]`.

OLX `CardParser`: маркеры карточек теперь атрибут класса
`CARD_RESOURCE_MARKERS` (обратная совместимость с модульной константой
сохранена) — платформы переопределяют их подклассом, вся классификация
текстов (цена/дата/ТОП/город) унаследована.

### Bootup — E2E-пайплайн подключения платформы
`aios_core/platforms/bootup.py` / `aios platforms bootup`:

1. **scaffold** — из APK (`aapt dump badging`, runner инъецируется) или
   из пары `--name/--package`; повторный запуск продолжает (resume)
   готовый скелет;
2. **register** — YAML-дескриптор регистрируется в реестре;
3. **calibrate** — дамп поисковой выдачи из `--dump`, инъецируемого
   `driver(package, query)` или generic-драйва по ADB (открыть
   приложение → пауза → `uiautomator dump`); без устройства шаг
   пропускается, статус `scaffolded`;
4. **hints → descriptor** — подсказки в `extras.parser_hints` YAML +
   перерегистрация (`write_hints_to_descriptor`, общий с CLI);
5. **codegen** — `card_parser.py` платформы из маркеров;
6. **verify** — дамп разбирается свежим парсером: карточки > 0 →
   статус `ready`.

`--dry-run` — все шаги возвращают планы без записей на диск. Итог —
JSON-отчёт по шагам (`scaffold/register/calibrate/hints/codegen/verify`).

```bash
aios platforms bootup --apk slando.apk --query "велосипед" --dry-run
aios platforms bootup --name slando --package com.slando.app --dump feed.xml
```

### REST-калибровка parser_hints
`POST /api/v1/platforms/{platform}/hints` с `{dump}` или `{hints}`:
сохраняет подсказки в runtime-дескриптор и возвращает
`parser_preview` — количество карточек и примеры заголовков
свежесобранным парсером. Персистентность в YAML — через CLI
(`platforms calibrate --write`).

### Прочее
- Scaffold YAML: описание дескриптора — двойные кавычки с
  экранированием (двоеточия в auto-scaffold description больше не ломают
  YAML-парсер).
- CLI `calibrate --write` и bootup используют общий
  `write_hints_to_descriptor()`.

## Установка

```bash
pip install aios-9.0.0a11-py3-none-any.whl
```

## Дальше (дорожная карта к 10000+)

- Калибровка детального экрана и мессенджера (паттерны OLX
  `detail.py`/`messenger.py`: описание/продавец, кнопка «Написати»).
- Bootup + DevicePool: автолизинг эмулятора для live-драйва
  (`ensure_device` + точечный драйв под flow поиска платформы).
- CI-регрессия маркеров: периодический re-calibrate на свежих сборках
  приложений, алёрт при смене resource-id.
