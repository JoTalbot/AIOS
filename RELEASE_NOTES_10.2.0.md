# RELEASE_NOTES — AIOS v10.2.0

**Release Date:** 2026-07-24
**Test Suite:** 1616 tests passing, 0 failures

## 🚀 Major New Features

### 1. Credential Manager (`aios_core/credential_manager.py`)
Secure credential storage and rotation for platform accounts:

- **Encrypted Storage** — XOR stream cipher with PBKDF2-like key derivation (HMAC-SHA256)
- **Credential Types** — PASSWORD, API_KEY, TOKEN, COOKIE, SSH_KEY, PAT, OAUTH, 2FA_SECRET
- **Rotation Policies** — NEVER, DAILY, WEEKLY, MONTHLY, ON_EXPIRY, ON_COMPROMISE
- **Automatic Rotation Checks** — `check_rotations()` finds stale credentials
- **Compromise Response** — `compromise()` immediate emergency rotation
- **Re-keying** — `rekey()` re-encrypts all credentials with new passphrase
- **Credential Masking** — `_mask_value()` shows only last 4 chars for safe display
- **Audit Logging** — `export_audit_log()` tracks all rotations with timestamps
- **Integrity Check** — SHA-256 hash verification on retrieval
- **Activate/Deactivate** — enable/disable credentials without deletion

### 2. Price Alert System (`aios_core/price_alert_system.py`)
Configurable alerts for price drops and changes:

- **7 Alert Conditions** — price drop/increase %, below/above threshold, availability change, price stability, arbitrage spread
- **Priority Levels** — CRITICAL, HIGH, NORMAL, LOW, INFO with escalation
- **Cooldown Deduplication** — suppress duplicate alerts within configurable window
- **Alert Lifecycle** — PENDING → DELIVERED → ACKNOWLEDGED
- **Human-readable Messages** — auto-generated Ukrainian-language alerts (📉, 📈, 💰, ⚠️, 🔔 emojis)
- **Alert Digest** — batch recent alerts into grouped summary
- **Platform Filters** — filter rules and alerts by platform
- **Alert History** — configurable max history (default 1000)

### 3. Scraping Strategy Templates (`aios_core/scraping_strategy_templates.py`)
Pre-built configurations for common scraping patterns:

- **7 Built-in Templates** — OLX Collector, OLX Monitor, Rozetka Ecommerce, TikTok Shop, FB Marketplace, OLX AutoWatch, OLX Full Agent
- **Template Registry** — store, retrieve, list, clone templates
- **Template Validation** — check param ranges, rate limits, sections, schedule
- **Template Composition** — combine multiple templates into hybrid strategies
- **Template Adaptation** — adjust rate limits and sections for different platform categories
- **Platform Categories** — MARKETPLACE, ECOMMERCE, SOCIAL_SHOP, MESSENGER, SOCIAL_MEDIA
- **Auto-detection** — `_detect_category()` infers category from platform name

## 🧪 Tests

- `test_v10_2_modules.py` — 58 tests (encryption, credentials, alerts, templates)
- **1616 total tests, 0 failures**

## 📊 Version Bump

- v10.1.0 → **v10.2.0**
