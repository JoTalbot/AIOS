# AIOS Official Release Notes — Version 9.0.0-alpha.3

**Release Tag:** `v9.0.0-alpha.3`  
**Release Date:** July 21, 2026  
**Repository:** `JoTalbot/AIOS`  
**Constitutional Compliance:** 100% (67 Articles Validated via `tula`)  
**Automated Test Coverage:** 648 / 648 Tests Passing (100% Green)

---

## 🌟 Executive Summary

`v9.0.0-alpha.3` turns the OLX Parser Agent into a complete trading cockpit:
market collection, personal messaging, own-listings care, automated
improvement/repost planning and alerting — all offline-tested (no device
required for the suite) and guarded at every action that can touch the
outside world.

---

## 🚀 What's New

### 📈 Market intelligence & tracking (storage v2)

- Price history per ad (`olx_sightings`), first/last-seen counters,
  `is_active` lifecycle (gone-from-feed = likely sold, revived on return).
- `PriceTracker`: price drops, gone ads; CSV/JSON export; CLI
  `aios olx collect|stats|recommend|export|history|drops`.

### 📄 Ad pages & 💬 personal chats (storage v3)

- `AdDetailParser`: full ad-page extraction (params, description, seller
  card, views).
- `OLXMessenger`: chat list/conversation parsers, rule-based
  `ReplySuggester` (availability, bargaining with min-price floor, meeting),
  **guarded outbox** — replies reach the device only via `auto_send=True`
  or an explicit flush. REST `/olx/chats`, `/olx/outbox*`.

### 🛡 Own-listings care & promotion

- `OwnAdsParser` + tracker: views/favorites/messages snapshots,
  `stagnant()` detection.
- `AdImprover` (title keywords, median-based price, description additions),
  `RepostPlanner` (evening best-hours), `Reposter` and `OwnAdEditor` —
  **DRY-RUN by default**, `confirm=True` required, duplicate-rules warning.

### 🔔 Subscriptions, favorites & AutoWatch (storage v4)

- `SubscriptionManager`: named filtered searches → new-ad alerts per cycle.
- `FavoritesWatch`: price drops on saved ads.
- `AutoWatch`: one-call unattended cycle (collect → alerts → own snapshot →
  stagnant → suggestions + repost plans → notifications).

### 🌐 Surfaces

- **REST**: 25+ endpoints under `/api/v1/modules/olx/*` (ads, stats,
  history, drops, detail, chats, outbox, own, subscriptions, favorites,
  notify, autowatch).
- **MCP tools**: `olx_market_stats`, `olx_listing_recommend`,
  `olx_price_drops` (constitution-guarded).
- **Dashboard OLX card**, full **CLI**, **`DEVICE_RUNBOOK.md`** live-device
  guide (ADBKeyBoard, calibration, cron, Telegram Bot API alerts).

---

## ✅ Verification

```bash
python -m pip install -r requirements.txt
python -m pytest -q        # 648 passed
python -m build            # dist/aios-9.0.0a3-*.{whl,tar.gz}
```

Previous notes: [RELEASE_NOTES_9.0_ALPHA2.md](RELEASE_NOTES_9.0_ALPHA2.md).
