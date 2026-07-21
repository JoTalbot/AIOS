# AIOS 9.0.0-alpha.16 — Reels-коллектор, Instagram autopilot, multi-account e2e

**Дата:** 2026-07-21 · **Тесты:** 850/850 зелёные

## Что нового

### 🎞 ReelsCollector — scroll-цикл видео-ленты (`platforms/reelscout.py`)
Generic коллектор Reels/клипов любой платформы каталога: цикл
«дамп → `HintVideoParser` → свайп» собирает уникальные видео-карточки
до лимита (`--max`, `max_swipes`) или пока `stop_after_empty` дампов
подряд не дадут новых. Парсер — из `content_categories.video_markers`
дескриптора (дефолт reel/video/clips); опциональный `driver(adb)`
открывает видео-вкладку (отказ — честный `RuntimeError`).

```bash
aios instagram reels --db data/instagram.sqlite --max 100
```

### 🧾 Generic receipts в storage
Видео-карточки не загрязняют таблицу объявлений: новая таблица
`olx_seen` + `check_and_record(fingerprint, kind="video")` /
`seen_count(kind)` — дедупликация между циклами (второй цикл по той
же ленте даёт 0 нового). Миграция бесшовная (`CREATE IF NOT EXISTS`).

### 🤖 `aios instagram autopilot` — полный цикл профиля
Одна команда = один JSON-отчёт (`steps`): сбор карточек → Reels →
Direct outbox-flush → опциональная guarded-публикация
(`--post-image/--post-text`, DRY-RUN без `--confirm`; `--login` для
pre-drive через login-стену). Guarded-философия без компромиссов:
Direct — только из одобренной очереди, публикация — только с явным
подтверждением.

```bash
aios instagram autopilot --db data/instagram.sqlite --login \
    --post-image photo.jpg --post-text "Нові кросівки!"   # план поста
```

`aios cron-plan --platform instagram` теперь генерирует строки
`instagram autopilot --login` (прочие платформы — generic autowatch,
OLX — родной, как раньше).

### 👥 Multi-account e2e через waitlist
Сквозной тест фиксирует контракт: два Instagram-профиля в очереди
FleetScheduler'а за одним устройством — честный `skipped-busy` при
занятости, последовательный запуск на одном serial после release,
раздельный `fleet:last_run:<platform>:<profile>` на профиль, повторный
запуск строго по `every_s`.

## Проверка
- **850 автотестов** (836 + 14 новых: reelscout, storage receipts,
  CLI reels/autopilot, cron-plan, multi-account e2e).
- Документация: `docs/PLATFORMS_SCALING.md`,
  `docs/modules/instagram/ONBOARDING.md`, `CHANGELOG.md`.

## Артефакты
- `aios-9.0.0a16-py3-none-any.whl`
- `aios-9.0.0a16.tar.gz`
