# AIOS v9.8.0 Release Notes

**Release Date**: 2026-07-24  
**Tag**: `v9.8.0`  
**Tests**: 1364 passing, 0 failures ✅

---

## TikTok Shop — Full Agent (10 modules)

| Module | Purpose |
|--------|---------|
| `collector.py` | ADB-driven video/product card collection with swipe scrolling |
| `card_parser.py` | TikTok-specific resource-id & text pattern extraction |
| `detail.py` | `TikTokVideoDetail` — description, hashtags, product tags, creator, likes/comments |
| `price_tracker.py` | Inherits `RozetkaPriceTracker` with 10% threshold (flash sales) |
| `autowatch.py` | Inherits `RozetkaAutoWatch` + trending hashtag detection |
| `favorites.py` | Inherits `RozetkaFavorites` — product wishlist |
| `auto_login.py` | Inherits `RozetkaAutoLogin` — TikTok package + rotate/puzzle captcha |
| `storage.py` | Inherits `OLXStorage` — ads, sightings, favorites, subscriptions |
| `messenger.py` | Inherits `HintsMessenger` — guarded outbox |
| `bootstrap.py` | Doctor via generic `platform_doctor` |

## Facebook Marketplace — Full Agent (10 modules)

| Module | Purpose |
|--------|---------|
| `collector.py` | ADB-driven Marketplace product collection |
| `card_parser.py` | FB-specific resource-id extraction |
| `detail.py` | FB listing detail parser (seller, location, price) |
| `price_tracker.py` | Inherits `RozetkaPriceTracker` with 5% threshold |
| `autowatch.py` | Inherits `RozetkaAutoWatch` |
| `favorites.py` | Inherits `RozetkaFavorites` |
| `auto_login.py` | Inherits `RozetkaAutoLogin` — FB package |
| `storage.py` | Inherits `OLXStorage` |
| `messenger.py` | Inherits `HintsMessenger` |
| `bootstrap.py` | Doctor via generic `platform_doctor` |

## WhatsApp — Enhanced Messenger Agent (6 modules)

| Module | Purpose |
|--------|---------|
| `contact_manager.py` | `ContactManager` — add/remove/search contacts with tags |
| `broadcast_scheduler.py` | `BroadcastScheduler` — approval-gated bulk messaging (compliance: never auto-send) |
| `chat_analytics.py` | `ChatAnalyzer` — outbox stats, response time, sentiment analysis |
| `messenger.py` | `WhatsAppMessenger` — guarded hints-based messaging |
| `storage.py` | `WhatsAppStorage` — inherits OLXStorage |
| `bootstrap.py` | `WhatsAppBootstrap` — doctor |

## Viber — Enhanced Messenger Agent (6 modules, inherits WhatsApp)

Same pattern as WhatsApp with Viber-specific package/deep-link.

---

## New CLI Subcommands

### TikTok Shop
```
aios tiktok-shop stats --query "iPhone"
aios tiktok-shop price-tracker drops --min-drop-pct 10 --db tiktok.sqlite
aios tiktok-shop autowatch --query "fashion" --no-collect
aios tiktok-shop favorites add/remove/list/drops
aios tiktok-shop doctor
```

### Facebook Marketplace
```
aios fb-marketplace stats --query "furniture"
aios fb-marketplace price-tracker drops/track
aios fb-marketplace autowatch --query "table" --no-collect
aios fb-marketplace favorites add/list
aios fb-marketplace doctor
```

### WhatsApp v2
```
aios whatsapp-v2 contacts list --tag vip
aios whatsapp-v2 contacts tag --jid john@s.whatsapp.net --tag vip
aios whatsapp-v2 broadcast create --text "Hello!" --tags vip
aios whatsapp-v2 broadcast approve --id broadcast_1
aios whatsapp-v2 broadcast list --status draft
aios whatsapp-v2 analytics
aios whatsapp-v2 doctor
```

### Viber v2
```
aios viber-v2 contacts list --tag vip
aios viber-v2 analytics
aios viber-v2 doctor
```

---

## New Tests (37 total)

- 11 TikTok (imports, storage, price_tracker drop/ignore, autowatch+trending, favorites, auto_login, deep_link, card_parser, detail)
- 9 Facebook (imports, storage, price_tracker, autowatch, favorites, auto_login, deep_link, detail empty/with_content)
- 11 WhatsApp (imports, contact dataclass, add/list/list_by_tag, broadcast create/approve/list/cancel, analytics, sentiment)
- 6 Viber (imports, storage_inherits, contact_manager, broadcast, analytics, sentiment)

---

## Architecture Pattern

All 4 platforms follow the v9.7.0+ scaffold template:
- **Commerce platforms** (TikTok, Facebook) → full Rozetka template (collector → card_parser → detail → price_tracker → autowatch → favorites → auto_login)
- **Messenger platforms** (WhatsApp, Viber) → contact_manager → broadcast_scheduler → chat_analytics

All inherit from proven base classes (OLXStorage, RozetkaPriceTracker, HintsMessenger) — zero code duplication.

---

## Breaking Changes
None — all changes are backward-compatible.

## Migration Guide
No migration required. Update `pip install aios==9.8.0`.

---

## Contributors
- JoTalbot (jo.talbot@gmail.com)

## Next: v9.9.0
- Price prediction ML, notification routing (Telegram/Slack/email)
- Seller reputation, image comparison, geospatial heatmap
- See [ROADMAP_NEXT.md](ROADMAP_NEXT.md) for full roadmap
