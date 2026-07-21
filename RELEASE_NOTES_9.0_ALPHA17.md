# AIOS 9.0.0-alpha.17 — Reels-вкладка, видео-алёрты, multi-host cron

**Дата:** 2026-07-21 · **Тесты:** 865/865 зелёные

## Что нового

### 📑 ReelsTabDriver — калибруемый тап по вкладке Reels
Перед scroll-циклом видео-ленты коллектор умеет сам открывать вкладку
Reels: маркеры вкладки калибруются в секцию
`extras.parser_hints.navigation.reels_tab` YAML-дескриптора
(`rid_markers`/`text_markers`; дефолт — типовые rid reels/clips и
подписи «Reels»). Узел ищется только с bounds, тап — по центру, без
хардкода координат; вкладка не найдена → честная ошибка (JSON `error`
в CLI). Резолвер `reels_driver_for(platform, directory)` — в том же
стиле, что `video_parser_for`.

```bash
aios instagram reels --open-tab --db data/instagram.sqlite
```

### 🔔 Видео-алёрты (video-new)
`ReelsCollector(notifier=...)` шлёт событие `video-new` в
WebhookNotifier только когда цикл принёс новые видео (дедуп через
receipts — повторный цикл алёрта не даёт). Payload: platform, new,
seen, query, sample-заголовки.

```bash
aios instagram reels --webhook https://hooks.example/in --open-tab
aios instagram autopilot --login --open-tab --webhook https://...
```

### 🗂 Multi-host cron-plan (--shard-map)
`aios cron-plan --shard-map` раскладывает cron-строки профилей по
липким HRW-маршрутам ShardRouter (`AIOS_SHARDS_DB`): заголовки
`# === host: worker-1 (base_url) · профилей: N ===`, немаршрутизиро-
ванные профили — в группе `local`, pool-monitor помечен «на каждом
хосте». Один сгенерированный файл раздаётся по нодам — sticky-
маршруты исключают двойной запуск профиля.

```bash
aios shards add node-1 http://10.0.0.1:8001
aios cron-plan --platform instagram --shard-map --write /etc/cron.d/aios
```

## Проверка
- **865 автотестов** (850 + 15 новых: tab driver, video-new алёрты,
  CLI `--open-tab`/`--webhook`, shard-map cron-план).
- Документация: `docs/PLATFORMS_SCALING.md`,
  `docs/modules/instagram/ONBOARDING.md`, `CHANGELOG.md`.

## Артефакты
- `aios-9.0.0a17-py3-none-any.whl`
- `aios-9.0.0a17.tar.gz`
