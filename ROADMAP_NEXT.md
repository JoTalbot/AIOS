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

## v9.5.0 🚧 (in progress — 3/5 done)
- ✅ Rozetka.ua platform scaffold (Storage, Messenger, Bootstrap, YAML)
- ✅ Rozetka CLI subcommand (stats, dm-send, dm-outbox, doctor)
- ✅ Rozetka calibration recipe (ecommerce kind: cards+detail+messenger+navigation)
- ✅ RateLimiter memory leak fix (bounded pruning + reset())
- 🔲 httpx2 full async migration (remaining sync tests)
- 🔲 Production dashboard React v2

**1247 tests, 0 failures**

## v9.6.0 (planned)
- Rozetka.ua full agent (collector, card_parser, detail, competitive)
- Rozetka.ua price tracker + price drop notifications
- Rozetka.ua autowatch + favorites
- Auto-login scaffold (Rozetka, OLX, Instagram)
- Benchmarks CI thresholds (blocking)

## v9.7.0 (planned)
- Multi-market cross-platform (OLX ↔ Rozetka price comparison)
- AI advisor: cross-platform recommendation engine
- Vector search / semantic product matching
- Real-time WebSocket dashboard updates

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
│   ├── rozetka/        # Rozetka scaffold (storage, messenger, bootstrap)
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

## Platform Scaffold Template

Each new marketplace follows this pattern:
1. `platforms/<name>.yaml` — descriptor with compliance config
2. `aios_core/modules/<name>/` — module package
3. `storage.py` — inherits OLXStorage (ads, price-history, outbox, own_ads, competitive)
4. `messenger.py` — approval-gated outbox (PACKAGE, DEEP_LINK)
5. `bootstrap.py` — doctor/preflight/calibration (inherits OLXBootstrap)
6. `aios_cli/<name>.py` — CLI subcommands (stats, dm-send, dm-outbox, doctor)
7. `tests/test_<name>_agent.py` + `test_<name>_cli.py` + `test_<name>_recipe.py`

---

## Release Instructions

### Docker (GHCR)
```bash
git tag v9.5.0
git push origin v9.5.0
# → CI builds multi-arch image, pushes to ghcr.io/JoTalbot/AIOS:v9.5.0
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
