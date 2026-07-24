# AIOS v9.4.0 Release Notes — Test Quality & Architecture Sprint

**Date:** 2026-07-24

---

## 🧪 Test Suite: 0 Failures

| Metric | v9.3.1 | v9.4.0 | Change |
|--------|--------|--------|--------|
| Tests passing | ~1100 | **1227** | +127 |
| Test failures | 104+ | **0** | ✅ |
| async fixture errors | 115 | **0** | ✅ |
| StarletteDeprecationWarning | 10 files | **0** | ✅ |
| Race condition (_PLATFORMS) | random 2-9 fails | **0** | ✅ |
| Docstring coverage | 73.9% | **100.0%** | ✅ |

### Critical Bug Fixes (10)

1. `storage.py`: removed `@lru_cache` from `new_id()` and `now_iso()` — deterministic uuid/timestamp
2. `orchestrator.py`: added `return task` in `create_task()` — was silently returning None
3. `marketplace.py`: added `return item` in `publish()` — was silently returning None
4. `api/mixins_core.py`: 3 missing imports (`PlainTextResponse`, `json`, `rate_limiter`)
5. `api/mixins_core.py` + `mixins_devices.py`: broken `@staticmethod` + `self` — TypeError via middleware
6. `android_ai_navigation.py`: split `_generate_screen_signature` → proper `classify()` + `_generate_screen_signature()`
7. `aios_cli.py`: argparse dest generation, missing subcommand args, bool type bug
8. `aios_cli/messengers.py`: `getattr()` fallbacks for missing Namespace attributes
9. `deploy/monitoring/aios-alerts.yml`: added 5 Prometheus alert rules + severity fix
10. `event_bus.py` + tests: `eb.on()` → `eb.subscribe()`, `eb.emit()` 3-arg API

---

## 🔄 Starlette → httpx Migration

All 8 test files migrated from sync `starlette.testclient.TestClient` to `async httpx.AsyncClient` with `ASGITransport`. Eliminates `StarletteDeprecationWarning` across the entire suite. `concurrent.futures.ThreadPoolExecutor` → `asyncio.gather` in load tests.

Files: `test_admin_api.py`, `test_h2_batch.py`, `test_onboard_messengers.py`, `chaos/test_chaos_resilience.py`, `e2e/test_admin_api_e2e.py`, `load/test_api_load.py`, `performance/test_api_performance.py`, `security/test_security.py`

---

## 🏎️ Race Condition Fix (_PLATFORMS)

Root cause: global mutable `_PLATFORMS` dict modified by tests in parallel (xdist). Fix: `snapshot_registry()` / `restore_registry()` + autouse `_isolate_platform_registry` fixture in `conftest.py`. Also made constitution/phase1 tests self-contained (no dependency on prior test execution order).

**Result:** 1227/1227 pass with `--dist loadgroup` (was random 2-9 failures).

---

## 📝 Type-Hints Migration (232 files)

`Dict[str, Any]` → `dict[str, Any]`, `List[str]` → `list[str]`, `Optional[str]` → `str | None`, `Tuple[int, int]` → `tuple[int, int]`, `Set[str]` → `set[str]`. Unused `typing` imports cleaned up.

---

## 📝 100% Docstring Coverage

462 docstrings added via safe AST-based script (no multiline-def corruption). Coverage: 73.9% → 84.9% → **100.0%**.

---

## 🔧 CI/CD

- `pyproject.toml`: v9.4.0, pytest-xdist, `[tool.pytest.ini_options]`, `[tool.black]`, `[tool.isort]`
- `Dockerfile`: multi-arch `BUILDPLATFORM` (amd64 + arm64)
- `ci.yml`: pytest-xdist `-n 4 --dist loadfile`, benchmarks job (non-blocking)
- Benchmarks CI: 12 stable benchmarks, 1 skipped (RateLimiter memory leak)

---

## 🧹 Repository Cleanup

15 stale branches deleted: 10 Dependabot + 1 fix + 2 feature + 2 session. Only `main` + `gh-pages` remain.

---

## 🔒 Security & Docs

- `SECURITY_FIX.md`: credential rotation checklist
- `ROADMAP_NEXT.md`: v9.4.0 achievements + v9.5.0 plan

---

## 📋 v9.5.0 Plan

- Rozetka.ua platform scaffold
- RateLimiter memory leak fix
- httpx2 full async migration
- Performance benchmarks CI thresholds
