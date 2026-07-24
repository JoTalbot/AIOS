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

## v9.7.0 🚧 (next)
- 🔲 Multi-market cross-platform comparator (OLX ↔ Rozetka ↔ Prom price comparison)
- 🔲 AI advisor v2: cross-platform recommendation engine + price prediction
- 🔲 Vector search / semantic product matching (embeddings + similarity)
- 🔲 Real-time WebSocket dashboard updates (live price alerts stream)
- 🔲 Benchmarks CI thresholds (blocking regression gate)
- 🔲 httpx2 full async migration (remaining sync tests → 0 sync)

## v9.8.0 (planned)
- TikTok full agent (collector, card_parser, detail, reels scout)
- WhatsApp/Viber/Facebook Marketplace full agents (not just scaffold)
- Multi-account fleet scheduler (per-platform 3+ profiles, cron-plan via-shards)
- Production dashboard React v3 (WebSocket, cross-platform charts)
- Mobile SDK (Flutter/React Native wrapper for AIOS REST API)

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
│   ├── calibrate.py    # Device calibration engine
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
├── rate_limiter.py     # Bounded sliding-window rate limiter
├── storage.py          # Database (no @lru_cache)
├── orchestrator.py     # Orchestrator (returns task)
└── ...
```

## Platform Scaffold Template (v9.6.0+)

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

### CLI & Tests
13. `aios_cli/<name>.py` — CLI subcommands (stats, dm-send, dm-outbox, doctor, price-tracker, autowatch, favorites, auto-login)
14. `tests/test_<name>_*.py` — agent, cli, recipe, price_tracker, autowatch, favorites, auto_login

---

## Release Instructions

### Docker (GHCR)
```bash
git tag v9.7.0
git push origin v9.7.0
# → CI builds multi-arch image, pushes to ghcr.io/JoTalbot/AIOS:v9.7.0
```

### SDK (PyPI)
```bash
git tag sdk-v4.2.0
git push origin sdk-v4.2.0
# → CI builds sdk/ and publishes aios-client to PyPI
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
