# AIOS v9.0.0-alpha.15 — Own-posts Instagram (guarded), VideoCards, FleetScheduler

**Дата:** 2026-07-21 · **Тесты:** 836 passing (+13)

Instagram умеет свои посты (счётчики + guarded-публикация), ленты без
цен получили собственный экстрактор видео-карточек, а циклы заботы всех
платформ балансируются по пулу устройств.

## Что нового

### Instagram own-posts (`modules/instagram/own_posts.py`)

- **`OwnPostsParser`** — посты профиля: подпись и счётчики
  лайков/комментариев/просмотров (`«1 234 перегляди»`,
  `«56 вподобань»`); `to_own_ad()` маппит в общий OwnAdsTracker —
  застой/предложения/repost-план AutoWatch работают на постах
  Instagram без изменений.
- **`PostComposer`** — публикация по guarded-философии: **DRY-RUN план
  по умолчанию**, `confirm=True` исполняет: `adb push` → deep link
  `instagram://library` → текстовые тапы Next → caption (ADBKeyBoard) →
  Share. Ноль координатных констант; смена верстки = честная ошибка
  шага с советом рекалибровки.
- CLI: `aios instagram own --db D [--dump grid.xml]`,
  `aios instagram post --image i.jpg --text "..." [--confirm]`.

### VideoCards (`platforms/videocards.py`)

Непродуктовый контент (Reels/клипы) без цены: `VideoCard` (подпись,
тайм-код, просмотры/лайки, fingerprint), `HintVideoParser` по
video-маркерам из `content_categories` калибровки (или дефолтным
reel/video/clips), `video_parser_for(platform)` из дескриптора.

### FleetScheduler (`platforms/fleetsched.py`)

Интервальные autowatch-джобы всех платформ/профилей на одном пуле
эмуляторов:

- аренда устройства на время цикла через DevicePool (общий SQLite —
  конкуренция между узлами решается механикой пула); занято →
  `skipped-busy` без штамповки last_run;
- ошибки джоба изолированы, аренда освобождается гарантированно;
- вернувшийся `marker_status: "drift"` → webhook-алёрт
  `marker-drift` (рецепт рекалибровки);
- CLI: `aios devices fleet-run --every-s 900 [--query Q] [--webhook URL]`.

## Установка

```bash
pip install aios-9.0.0a15-py3-none-any.whl
```

## Дальше (дорожная карта к 10000+)

- Reels-коллектор: scroll-цикл видео-ленты → video storage (та же
  OLXStorage-схема, cards без цены).
- Комплексный `aios instagram autopilot`: own-posts + Direct +
  FleetScheduler под одним профилем (cron-plan генератор расширить).
- Multi-account Instagram: профили N штук (DevicePool + waitlist уже
  готовы) — e2e прогон двух аккаунтов на одном узле.
