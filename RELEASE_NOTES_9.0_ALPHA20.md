# AIOS 9.0.0-alpha.20 — onboarding wizard, WhatsApp/Viber/TikTok, pull-first jobs

**Дата:** 2026-07-21 · **Тесты:** 906/906 зелёные

Мега-батч H2: единый вход подключения платформы, три новые платформы
из коробки (мессенджеры WhatsApp/Viber + video-first TikTok) и
pull-модель как способ эксплуатации.

## Что нового

### 🪄 Onboarding wizard
`aios onboard com.example.app` — fetch (apkeep) → bootup
(scaffold→register→calibrate→codegen→verify) → **паспорт готовности**
{scaffolded, registered, hints_card_markers, parser_codegen,
verified_cards} + честные next_commands («needs device» вместо
заглушек):

```bash
aios onboard com.example.app --fetch --dump search.xml --serial emulator-5554
```

### 💬 Generic messenger-платформы: WhatsApp, Viber, TikTok
`HintsMessenger` — guarded-мессенджер целиком из calibrated hints:
outbox-по-умолчанию (ничего не уходит на устройство молча), flush по
одобрению, inbox-тап deep-link (`whatsapp://`, `viber://chats`), список
диалогов по chat/bubble-маркерам. Платформа = 3 тонких класса +
YAML c `extras.compliance` (autopost_allowed: false, messenger:
approval-only). Generic `platform_doctor` — чек-лист готовности.

```bash
aios whatsapp doctor
aios whatsapp dm-send --chat chat:anna --text "Добрий день!"   # в очередь
aios whatsapp dm-flush
aios viber chats
aios platforms reels --platform tiktok --open-tab --max 100    # video-first
aios platforms doctor --platform tiktok
```

### 🔁 Pull-first автоматизация + jobs REST
- `cron-plan --via-shards`: cron только вешает джобы
  (`shards enqueue`), исполняют ноды-воркеры; платформы без builtin-вида
  — честный комментарий.
- REST-плоскость очереди для dashboard:
  `GET/POST /api/v1/shards/jobs`, `GET /api/v1/shards/stats`.

## Проверка
- **906 автотестов** (892 + 14 новых: каталог пакетов, HintsMessenger
  guarded-контур, doctor, wizard, generic reels/doctor CLI, cron
  via-shards, jobs REST).
- Документация: `docs/ROADMAP_FULL.md` (H2.6 ✅, H2.7/H2.8 частично),
  `docs/PLATFORMS_SCALING.md`, `CHANGELOG.md`.

## Артефакты
- `aios-9.0.0a20-py3-none-any.whl`
- `aios-9.0.0a20.tar.gz`
