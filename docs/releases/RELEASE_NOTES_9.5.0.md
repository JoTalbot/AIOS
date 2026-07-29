# AIOS v9.5.0 Release Notes

**Release Date**: 2024-07-24  
**Tag**: `v9.5.0`  
**Tests**: 1254 passing, 0 failures ✅

---

## Critical Bug Fixes

### `@lru_cache` on `Database.new_id()` and `Database.now_iso()` (storage.py)
- `uuid4()` was called once and cached — every `new_id()` returned the **same UUID**
- `now_iso()` returned a **frozen timestamp** — caused UNIQUE constraint failures and TTL test failures
- **Fix**: Removed `@lru_cache` from both methods

### Missing `return` statements
- `Orchestrator.create_task()` silently returned `None` — callers got no task object
- `CapabilityMarketplace.publish()` silently returned `None` — callers got no item
- **Fix**: Added `return task` and `return item`

### Broken `@staticmethod` with `self` usage
- `_bounded_int()` and `_memory_actor()` in `mixins_core.py` had `@staticmethod` but referenced `self`
- `_shard_jobs()` and `_shards_add()` in `mixins_devices.py` — same issue
- **Fix**: Removed `@staticmethod` / added `self` parameter

### Missing imports causing NameError
- `PlainTextResponse`, `json`, `rate_limiter` missing in `mixins_core.py`
- **Fix**: Added all missing imports

### `AIScreenClassifier.classify()` logic embedded in signature method
- `_generate_screen_signature()` contained classify logic, returning `ScreenEmbedding` instead of `str`
- **Fix**: Split into proper `classify(xml)` → `ScreenEmbedding` and `_generate_screen_signature(xml)` → `str`

### `argparse dest` bug and `isinstance(True, int)`
- `dest=f"{an[2:]}_dest"` created mismatched attribute names on `Namespace`
- `type=int` for bool-default arguments caused `isinstance(True, int)` → `True`
- **Fix**: Removed dest override; added `not isinstance(av, bool)` guard

### CLI attribute mismatches
- `args.interlocutor`, `args.max_cards`, `args.marker`, `args.status`, `args.pace_actions`, `args.pace_jitter` not found
- **Fix**: Added `getattr()` fallbacks for all 6 attributes

### EventBus API mismatch
- `eb.on()` → `eb.subscribe()`, `eb.emit("test", {"x":1})` → `eb.emit("test", "test_source", {"x":1})`
- **Fix**: Updated test_integration_full_stack.py

### `subscription_list` → `subscriptions_list`
- Three agent tests (bigl, prom, shafa) used wrong method name
- **Fix**: Corrected to `subscriptions_list`

---

## Async & Test Infrastructure

### 115+ async fixtures fixed
- `@pytest.fixture` → `@pytest_asyncio.fixture` in 9 test files
- Async test methods inside classes now have `@pytest.mark.asyncio`

### Starlette → httpx migration
- All 8+ test files migrated from `starlette.testclient.TestClient` → `httpx.AsyncClient` with `ASGITransport`
- **0 TestClient references remain** in the entire test suite

### `_PLATFORMS` race condition fix (pytest-xdist)
- Shared `_PLATFORMS` global dict caused failures with parallel execution
- **Fix**: `snapshot_registry()` / `restore_registry()` (full dict, not just keys) + autouse `_isolate_platform_registry` fixture
- Constitution/phase1 tests now self-contained (no dependency on execution order)

---

## Type Hints & Documentation

### Modern type hints migration (232 files)
- `Dict[str, Any]` → `dict[str, Any]`
- `List[str]` → `list[str]`
- `Optional[str]` → `str | None`
- `Tuple[int, int]` → `tuple[int, int]`
- `Set[str]` → `set[str]`
- Unused `typing` imports cleaned up

### 462 docstrings added → 100% coverage
- Every public function, class, and method now has a docstring

### RateLimiter memory leak fix
- `RateLimiter.is_allowed()` grew `self.requests[key]` list unbounded — caused benchmark timeouts (>60s)
- **Fix**: Prunes expired timestamps on every call, added `reset(key|None)` method
- Benchmark now runs in **<1s**

---

## Rozetka.ua Platform (New!)

### Full scaffold
- `Storage` — Rozetka-specific storage adapter
- `Messenger` — DM/messaging integration
- `Bootstrap` — Platform bootstrap & configuration

### Agent components
- `Collector` — Catalog collection & deep-link resolution
- `CardParser` — Card data extraction
- `DetailParser` — Product detail parsing

### CLI subcommand
- `aios rozetka stats` — Platform statistics
- `aios rozetka dm-send` — Send direct message
- `aios rozetka dm-outbox` — DM outbox management
- `aios rozetka doctor` — Health check

### Calibration recipe
- Added `ecommerce` kind to `_KIND_HINTS`: `cards + detail + messenger + navigation` (4 sections)
- 5 recipe tests: ecommerce kind, partial, ready, marketplace, unknown

---

## CI/CD & Infrastructure

### pytest-xdist parallel execution
- CI now runs tests with `-n 4 --dist loadfile` for speed

### Benchmarks job
- Separate CI job for benchmark validation

### Dockerfile multi-arch support
- `BUILDPLATFORM` for amd64 + arm64 builds

### Prometheus alerts
- 5 missing alert rules added to `deploy/monitoring/aios-alerts.yml`

### Dashboard v2
- Uptime counter (JS)
- Version badge v9.5
- Fixed `.format()` JS brace conflict (`{` → `{{`)

### Dependabot & cleanup
- All 10 Dependabot PRs merged into main
- 15 stale branches deleted (10 Dependabot + 1 fix + 2 feature + 2 session)

---

## Breaking Changes
None — all changes are backward-compatible.

## Migration Guide
No migration required. Update `pip install aios==9.5.0`.

---

## Contributors
- JoTalbot (jo.talbot@gmail.com)

## Next: v9.6.0
- Rozetka price tracker, autowatch, favorites, auto-login scaffold
- See [ROADMAP_NEXT.md](https://github.com/JoTalbot/AIOS/blob/main/ROADMAP_NEXT.md) for full roadmap
