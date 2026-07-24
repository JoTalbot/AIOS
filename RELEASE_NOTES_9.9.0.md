# AIOS v9.9.0 Release Notes

**Release Date**: 2026-07-24  
**Tag**: `v9.9.0`  
**Tests**: 1404 passing, 0 failures ✅

---

## New Modules (aios_core/)

### notification_router.py — Smart Notification Routing
- `NotificationChannel` — EMAIL, TELEGRAM, SLACK, PUSH, WEBHOOK
- `Severity` — INFO, WARNING, CRITICAL with severity-based filtering
- `NotificationPreferences` — per-channel preferences with min_severity gate
- `NotificationRouter` — routes alerts to appropriate channels based on preferences
- `send(message)` — dispatches to all enabled channels for the message severity
- `_send_telegram`, `_send_slack`, `_send_email`, `_send_push`, `_send_webhook`
- `history()` — delivery history tracking
- Telegram Bot API, Slack webhook, SMTP email, generic webhook all supported

### seller_reputation.py — Seller Reputation Scoring
- `SellerReputationScorer` — composite 0-100 score from 4 factors
- **Activity (40%)** — listing count, frequency
- **Price consistency (30%)** — price std deviation relative to average
- **Listing quality (20%)** — title/description completeness
- **Response time (10%)** — outbox reply speed
- `score_seller(seller_id)` — individual seller score
- `score_all_sellers()` — ranked list of all sellers
- Letter grades: A (≥90), B (≥75), C (≥60), D (≥40), F (<40)

### geospatial_heatmap.py — City-Level Pricing Analysis
- `GeospatialPriceAnalyzer` — compute city-level price statistics
- `CityPriceStats` — per-city count, avg, min, max, std
- `PriceHeatmap` — full heatmap with cheapest/priciest cities, national average
- `best_buy_cities(query, limit)` — cheapest cities for buying
- `best_sell_cities(query, limit)` — priciest cities for selling
- `arbitrage_cities(query, min_spread_pct)` — city pairs with price arbitrage

---

## Bigl/Prom/Shafa — Upgrade from Scaffold to Full Agent

### Bigl.ua (5 new modules)
- `BiglCollector` — ADB-driven product collection with deep links
- `BiglPriceTracker` — inherits RozetkaPriceTracker
- `BiglAutoWatch` — inherits RozetkaAutoWatch (platform="bigl")
- `BiglFavorites` — inherits RozetkaFavorites

### Prom.ua (5 new modules)
- `PromCollector` — ADB-driven product collection
- `PromPriceTracker` — inherits RozetkaPriceTracker
- `PromAutoWatch` — inherits RozetkaAutoWatch (platform="prom")
- `PromFavorites` — inherits RozetkaFavorites

### Shafa.ua (5 new modules)
- `ShafaCollector` — ADB-driven product collection
- `ShafaPriceTracker` — inherits RozetkaPriceTracker
- `ShafaAutoWatch` — inherits RozetkaAutoWatch (platform="shafa")
- `ShafaFavorites` — inherits RozetkaFavorites

All three inherit from Rozetka pattern — zero code duplication.

---

## New Tests (40 total)

- 11 notification_router (channels, severity, prefs defaults, channels_for_severity, min_severity, message dict, send telegram/slack/email, history, no_channels)
- 7 seller_reputation (dataclasses, empty, single seller, grade thresholds, activity, price consistency, score_all)
- 7 geospatial_heatmap (dataclasses, empty, with_data, best_buy, best_sell, arbitrage)
- 15 Bigl/Prom/Shafa (imports, storage_inherits, price_tracker, autowatch platforms, favorites add/remove, deep links)

---

## Breaking Changes
None — all changes are backward-compatible.

## Migration Guide
No migration required. Update `pip install aios==9.9.0`.

---

## Contributors
- JoTalbot (jo.talbot@gmail.com)
