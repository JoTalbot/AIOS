# AIOS Roadmap — Next Milestones

## v9.4.0 ✅ (2026-07-24)
- 1227 tests passing, 0 failures (xdist parallel, 26s)
- 232 files: type-hints migration (Dict→dict, List→list, Optional→|None)
- 10 critical bug fixes (lru_cache, missing returns, @staticmethod+self, imports)
- Starlette → httpx async migration (8 test files, 0 DeprecationWarnings)
- _PLATFORMS race condition fix (snapshot/restore fixture)
- 462 docstrings → 100% coverage
- CI/CD: pytest-xdist, benchmarks job, pyproject.toml config
- Prometheus alerts: 5 new rules
- 15 stale branches deleted
- Docker: multi-arch support (amd64+arm64)

## v9.5.0 🚧 (in progress)
- Rozetka.ua platform scaffold (Storage, Messenger, Bootstrap, CLI)
- RateLimiter memory leak fix
- httpx2 full async migration (all remaining sync tests)
- Rozetka calibration recipe (cards, detail, messenger)
- Full production dashboard React v2

## v9.6.0 (planned)
- Rozetka.ua full agent (collector, card_parser, detail, competitive)
- Rozetka.ua price tracker + price drop notifications
- Rozetka.ua autowatch + favorites
- Auto-login scaffold (Rozetka, OLX, Instagram)

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
