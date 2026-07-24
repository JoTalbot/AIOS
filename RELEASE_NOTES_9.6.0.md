# AIOS v9.6.0 Release Notes

**Release Date**: 2026-07-24  
**Tag**: `v9.6.0`  
**Tests**: 1291 passing, 0 failures ✅

---

## New Modules (aios_core/modules/rozetka/)

### price_tracker.py — Price Drop Detection & Tracking
- `RozetkaPriceTracker` — configurable drop detection (min_drop_pct, min_absolute_drop)
- `PriceDropAlert` — alert object with fingerprint, old_price, new_price, drop_pct
- `detect_drops(since=None)` — scan all stored products for qualifying price drops
- `track_product(fingerprint)` — stats: current_price, min_price, max_price, price_count, history

### autowatch.py — Full AutoWatch Cycle
- `RozetkaAutoWatch` — orchestrates one full care cycle:
  1. Collect product cards via RozetkaCollector
  2. Store sightings in RozetkaStorage
  3. Detect price drops via RozetkaPriceTracker
  4. Find stagnant products (not seen for min_age_days)
  5. Check favorites for price changes
- `run_cycle(queries, collect)` — returns report dict with collection, price_drop_alerts, stagnant, favorite_alerts

### favorites.py — Favorites with Price-Change Awareness
- `RozetkaFavorites` — manage favorite products with price tracking
- `add(fingerprint)` / `remove(fingerprint)` / `list_all()` — basic CRUD
- `list_with_details()` — favorites with product details and current price
- `check_drops()` — detect price drops in all favorite products

### auto_login.py — Auto-Login Scaffold
- `LoginState` enum — NOT_STARTED, APP_OPENED, LOGIN_SCREEN_FOUND, CREDENTIALS_ENTERED, CAPTCHA_REQUIRED, TWO_FA_REQUIRED, LOGIN_SUCCESS, LOGIN_FAILED
- `LoginResult` dataclass — state, message, timestamp, session_id, retry_count
- `detect_login_screen(xml_dump)` — detect login form from UI XML dump
- `attempt_login(email, password, xml_dump)` — attempt login with graceful captcha/2FA detection
- `check_session()` — check current login session status

---

## New CLI Subcommands

### Price Tracker
```
aios rozetka price-tracker drops --min-drop-pct 5 --min-abs-drop 1
aios rozetka price-tracker track --fingerprint <fp>
```

### AutoWatch
```
aios rozetka autowatch --query "iPhone 16" --min-drop-pct 5 --min-age-days 3
aios rozetka autowatch --no-collect
```

### Favorites
```
aios rozetka favorites add --fingerprint <fp>
aios rozetka favorites remove --fingerprint <fp>
aios rozetka favorites list --details
aios rozetka favorites drops --min-drop-pct 5
```

### Auto-Login
```
aios rozetka auto-login check
aios rozetka auto-login attempt --email user@example.com --password secret
```

---

## New Tests (37 total)

### test_rozetka_price_tracker.py (7 tests)
- no_drops_on_stable_price, detects_drop, ignores_small_drop, track_product, track_product_empty, alert_to_dict, minimum_absolute_drop

### test_rozetka_autowatch.py (5 tests)
- run_cycle_no_collect, detects_price_drops, no_drops_stable, stagnant_products, favorite_alerts

### test_rozetka_favorites.py (7 tests)
- add, add_duplicate, remove, remove_nonexistent, list_with_details, check_drops, check_drops_no_change

### test_rozetka_auto_login.py (10 tests)
- state_values, result_defaults, detect_empty, detect_markers, detect_already_logged_in, detect_no_markers, attempt_no_credentials, attempt_with_captcha, attempt_with_2fa, result_state_serializes

### test_rozetka_cli_v960.py (8 tests)
- price_tracker_drops, price_tracker_track, autowatch_no_collect, favorites_add_remove, favorites_list, auto_login_check, auto_login_attempt, subparsers_registered

---

## Breaking Changes
None — all changes are backward-compatible.

## Migration Guide
No migration required. Update `pip install aios==9.6.0`.

---

## Contributors
- JoTalbot (jo.talbot@gmail.com)

## Next: v9.7.0
- Multi-market cross-platform (OLX ↔ Rozetka price comparison)
- AI advisor: cross-platform recommendation engine
- Vector search / semantic product matching
- See [ROADMAP_NEXT.md](ROADMAP_NEXT.md) for full roadmap
