# AIOS Roadmap — Next Milestones

## v9.4.0 ✅ (2026-07-24)
- 1227 tests passing, 0 failures (xdist parallel, 26s)
- 232 files: type-hints migration (Dict→dict, List→list, Optional→|None)
- 10 critical bug fixes (lru_cache, missing returns, @staticmethod+self, imports)
- CI/CD: pytest-xdist, loadfile distribution, pyproject.toml config
- Prometheus alerts: 5 new rules (shard workers, queue, stale claims, fleet, outbox)
- SECURITY_FIX.md: credential rotation checklist
- Docker: multi-arch support (amd64+arm64)
- argparse: fixed dest generation, added promote-budget, post-text args

## v9.5.0 (planned)
- 100% docstring coverage for public methods
- Performance benchmarks CI integration
- Starlette httpx2 migration (async test rewrite)
- Dependabot PR batch merge
- Rozetka.ua platform scaffold
- Full production dashboard React v2

## Release Instructions

### Docker (GHCR)
```bash
git tag v9.4.0
git push origin v9.4.0
# → CI builds multi-arch image, pushes to ghcr.io/JoTalbot/AIOS:v9.4.0
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
