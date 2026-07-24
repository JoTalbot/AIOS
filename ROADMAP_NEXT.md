# AIOS Roadmap — Next Milestones

## v9.4.0 ✅ (2026-07-24)
- 1227 tests, 0 failures, 0 warnings, 100% docstrings
- 10 critical bug fixes (lru_cache, missing returns, @staticmethod+self, imports)
- Starlette → httpx async migration (8 files, 0 DeprecationWarnings)
- _PLATFORMS race condition fix (snapshot/restore fixture)
- 462 docstrings → 100% coverage
- CI/CD: pytest-xdist, benchmarks job, Prometheus alerts
- 15 stale branches deleted
- Docker: multi-arch (amd64+arm64)

## v9.5.0 ✅ (2026-07-24)
- ✅ Rozetka.ua platform scaffold (Storage, Messenger, Bootstrap, YAML)
- ✅ Rozetka CLI subcommand (stats, dm-send, dm-outbox, doctor)
- ✅ Rozetka calibration recipe (ecommerce kind: cards+detail+messenger+navigation)
- ✅ RateLimiter memory leak fix (bounded pruning + reset())
- ✅ Rozetka full agent (Collector, CardParser, DetailParser)
- ✅ Dashboard v2: uptime counter, version badge v9.5
- ✅ RELEASE_NOTES_9.5.0.md + GitHub Release v9.5.0
- ✅ All 10 Dependabot PRs merged, 15 stale branches deleted

**1254 tests, 0 failures**

## v9.6.0 ✅ (2026-07-24)
- ✅ Rozetka.ua price tracker (PriceDropAlert, detect_drops, track_product)
- ✅ Rozetka.ua AutoWatch cycle (collect → price alerts → stagnant → favorites)
- ✅ Rozetka.ua favorites (add/remove/list/details/check_drops)
- ✅ Rozetka.ua auto-login scaffold (LoginState, detect_login_screen, attempt_login, captcha/2FA)
- ✅ Rozetka CLI price-tracker/autowatch/favorites/auto-login subcommands
- ✅ 37 new tests (1291 total, 0 failures)
- ✅ RELEASE_NOTES_9.6.0.md + GitHub Release v9.6.0

**1291 tests, 0 failures**

## v9.7.0 ✅ (2026-07-24)
- ✅ Cross-platform comparator (OLX ↔ Rozetka ↔ Prom ↔ Shafa price comparison + arbitrage)
- ✅ AI advisor v2 (cross-platform recommendations + price prediction + full analysis)
- ✅ Vector search engine (TF-IDF product matching — no external dependencies)
- ✅ WebSocket dashboard (real-time price alert streaming event bus)
- ✅ Benchmarks CI thresholds (blocking regression gate — 10 thresholds)
- ✅ CLI cross-platform/advisor-v2/search/benchmarks subcommands
- ✅ 47 new tests (1327 total, 0 failures)

**1327 tests, 0 failures**

## v9.8.0 ✅ (2026-07-24)
- ✅ TikTok Shop full agent (10 modules: collector, card_parser, detail, price_tracker, autowatch, favorites, auto_login)
- ✅ Facebook Marketplace full agent (10 modules: same pattern)
- ✅ WhatsApp enhanced messenger (6 modules: contact_manager, broadcast_scheduler, chat_analytics)
- ✅ Viber enhanced messenger (6 modules: inherits WhatsApp pattern)
- ✅ CLI tiktok-shop/fb-marketplace/whatsapp-v2/viber-v2 subcommands
- ✅ 37 new tests (1364 total, 0 failures)
- ✅ RELEASE_NOTES_9.8.0.md + GitHub Release v9.8.0

**1364 tests, 0 failures**

## v9.9.0 (planned)
- Price prediction ML model (linear → polynomial regression → LSTM)
- Smart notification routing (email, Telegram, Slack, Push)
- Product image comparison (CV-based similarity)
- Seller reputation scoring
- Geospatial price heatmap (city-level pricing analysis)

## v10.0.0 (long-term)
- Sovereign AGI reflection engine → metacognitive goal audit
- Universal invariant prover → symbolic theorem proving
- Multi-dimensional world model → counterfactual simulation rollouts
- Quantum-native QAOA task scheduling
- Neuromorphic LIF spiking engine → STDP unsupervised plasticity
- Substrate convergence (Silicon ↔ Photonic ↔ Neuromorphic ↔ Quantum ↔ Bio-compute)

---

## Architecture Overview

```
aios_core/
├── platforms/          # Platform registry, descriptor, catalog
│   ├── descriptor.py   # _PLATFORMS registry + snapshot/restore
│   ├── recipe.py       # Calibration recipes (messenger, collector, marketplace, ecommerce)
│   └── ...
├── modules/
│   ├── olx/            # Full OLX agent (21 files)
│   ├── rozetka/        # Rozetka full agent (10 files)
│   │   ├── storage.py       # RozetkaStorage (inherits OLXStorage)
│   │   ├── messenger.py     # Approval-gated outbox
│   │   ├── bootstrap.py     # Doctor/preflight/calibration
│   │   ├── collector.py     # Automated scrolling collection
│   │   ├── card_parser.py   # Rozetka card parser
│   │   ├── detail.py        # Rozetka detail parser
│   │   ├── price_tracker.py # Price drop detection & tracking
│   │   ├── autowatch.py     # Full AutoWatch cycle
│   │   ├── favorites.py     # Favorites with price-change alerts
│   │   └── auto_login.py    # Auto-login scaffold (captcha/2FA)
│   ├── instagram/      # Instagram agent
│   ├── facebook/       # Facebook messenger
│   ├── whatsapp/       # WhatsApp messenger
│   ├── viber/          # Viber messenger
│   ├── tiktok/         # TikTok scaffold
│   ├── bigl/           # Bigl scaffold
│   ├── prom/           # Prom scaffold
│   └── shafa/          # Shafa scaffold
├── cross_platform_comparator.py  # OLX ↔ Rozetka ↔ Prom ↔ Shafa
├── ai_advisor.py       # AI Advisor v1 (draft replies, price advice)
├── ai_advisor_v2.py    # AI Advisor v2 (cross-platform recommendations, prediction)
├── vector_search.py    # TF-IDF vector search engine
├── ws_dashboard.py     # WebSocket real-time event streaming
├── benchmarks_thresholds.py  # CI regression gate
├── rate_limiter.py     # Bounded sliding-window rate limiter
├── storage.py          # Database (no @lru_cache)
├── orchestrator.py     # Orchestrator (returns task)
└── ...
```

## Platform Scaffold Template (v9.7.0+)

Each new marketplace follows this pattern:

### Core (v9.3+)
1. `platforms/<name>.yaml` — descriptor with compliance config
2. `aios_core/modules/<name>/` — module package
3. `storage.py` — inherits OLXStorage (ads, price-history, outbox, own_ads, competitive)
4. `messenger.py` — approval-gated outbox (PACKAGE, DEEP_LINK)
5. `bootstrap.py` — doctor/preflight/calibration (inherits OLXBootstrap)

### Agent (v9.5+)
6. `collector.py` — ADB-driven scrolling card collection
7. `card_parser.py` — platform-specific card parsing
8. `detail.py` — product detail extraction

### Monitoring (v9.6+)
9. `price_tracker.py` — price drop detection (min_drop_pct, min_absolute_drop)
10. `autowatch.py` — full AutoWatch cycle (collect, alerts, stagnant, favorites)
11. `favorites.py` — favorites with price-change awareness
12. `auto_login.py` — auto-login scaffold (captcha/2FA handling)

### Cross-Platform (v9.7+)
13. Cross-platform comparator (OLX ↔ Rozetka ↔ Prom ↔ Shafa)
14. AI advisor v2 (cross-platform recommendations + price prediction)
15. Vector search (TF-IDF semantic product matching)
16. WebSocket dashboard (real-time price alert streaming)

### CLI & Tests
17. `aios_cli/<name>.py` — CLI subcommands (stats, dm-send, dm-outbox, doctor, price-tracker, autowatch, favorites, auto-login)
18. `tests/test_<name>_*.py` — agent, cli, recipe, price_tracker, autowatch, favorites, auto_login

---

## Release Instructions

### Docker (GHCR)
```bash
git tag v9.8.0
git push origin v9.8.0
# → CI builds multi-arch image, pushes to ghcr.io/JoTalbot/AIOS:v9.8.0
```

### Full Production Deploy
```bash
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml --profile bot up -d  # with Telegram
```

---

## Version History

| Версия | Дата | Тесты | Главное |
|--------|------|-------|---------|
| 9.0.0 | 2026-07-21 | 939 | Compliance + telemetry + audit-log + FB Marketplace |
| 9.1.0 | 2026-07-22 | 1000 | Android M7/M8 + AI Advisor + SDK v4.2 + Marketplace v2 |
| 9.2.0 | 2026-07-22 | 1010 | Production Autopilot 3 IG 2w ban-free sim 93.3% |
| 9.3.0 | 2026-07-22 | 1040 | Bug fixes + async fixtures + type hints start |
| 9.4.0 | 2026-07-24 | 1227 | 10 critical fixes + httpx migration + 462 docstrings |
| 9.5.0 | 2026-07-24 | 1254 | Rozetka.ua scaffold + agent + RateLimiter leak fix |
| 9.6.0 | 2026-07-24 | 1291 | Rozetka price tracker + AutoWatch + favorites + auto-login |
| 9.7.0 | 2026-07-24 | 1327 | Cross-platform comparator + AI v2 + vector search + WebSocket + benchmarks thresholds |
