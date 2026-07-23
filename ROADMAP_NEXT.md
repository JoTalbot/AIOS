# AIOS Roadmap — Next Milestones

## v9.3.1 ✅ (2026-07-23)
- 48+ commits: code quality sprint
- 0 bare excepts, 0 unannotated passes
- 272 test files, 1500+ test functions
- 106 modules with __all__, 478 -> None annotations
- Infrastructure: quality checker, githooks, linting configs

## v9.4.0 (planned)
- Full type-hint generics migration (Dict → dict[str, Any])
- 100% docstring coverage
- Performance benchmarks CI integration
- Multi-architecture Docker builds (arm64)

## Release Instructions

### Docker (GHCR)
```bash
git tag v9.3.1
git push origin v9.3.1
# → CI builds multi-arch image, pushes to ghcr.io/JoTalbot/AIOS:v9.3.1
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
