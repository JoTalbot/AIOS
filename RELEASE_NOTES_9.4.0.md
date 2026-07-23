# AIOS v9.4.0 Release Notes — Test & Core Quality Sprint

**Date:** 2026-07-24 | **Branch:** `fix/test-fails-and-v9.4-upgrades`

---

## 🧪 Test Suite Improvements

| Metric | v9.3.1 | v9.4.0 | Change |
|--------|--------|--------|--------|
| Tests passing | ~1100 | **1214** | +114 |
| Test regressions fixed | 0 | **15+** | ✅ |
| async fixture errors | 115 | **0** | ✅ |
| StarletteDeprecationWarning | 1 | 1 (non-blocking) | — |

### Critical Bug Fixes

1. **`storage.py`: removed `@lru_cache` from `new_id()` and `now_iso()`**
   - Both were returning identical values on every call, causing UNIQUE constraint
     failures in memory items and TTL expiry never happening.
   - Root cause: `@lru_cache(maxsize=128)` made uuid4 deterministic.

2. **`orchestrator.py`: added `return task` in `create_task()`**
   - Method was silently returning None, breaking all orchestrator tests.

3. **`marketplace.py`: added `return item` in `publish()`**
   - Method was silently returning None.

4. **`api/mixins_core.py`: 3 missing imports fixed**
   - `PlainTextResponse` → NameError in `/metrics`
   - `json` → NameError in `/rpc` endpoints
   - `rate_limiter` → NameError in task creation

5. **`api/mixins_core.py`: broken `@staticmethod` on `_bounded_int` and `_memory_actor`**
   - Both used `@staticmethod` but referenced `self`, causing TypeError via middleware → 400.

6. **`api/mixins_devices.py`: broken `@staticmethod` on `_shard_jobs` and `_shards_add`**
   - Same pattern — `@staticmethod` with `self` parameter.

7. **`android_ai_navigation.py`: split `_generate_screen_signature` into proper methods**
   - Old code had the classify logic embedded inside a signature generator,
     returning `ScreenEmbedding` from a method that should return `str`.
   - Added proper `classify(xml)` → `ScreenEmbedding` method.

8. **`aios_cli.py`: argparse dest generation & missing subcommand args**
   - Removed broken `_dest` suffix generation.
   - Added `--promote-budget`, `--promote-min-age-days`, `--post-text`,
     `--own-dump`, `--pace-actions`, `--pace-jitter` to autopilot.
   - Added `--db/--serial/--directory` to `reels` and `post` subcommands.
   - Fixed `type=int` bug for `bool(True)` args (Python: `isinstance(True, int)`).

9. **`aios_cli/messengers.py`: `args.interlocutor` → `getattr(args, "interlocutor", None)`**

10. **`deploy/monitoring/aios-alerts.yml`: added 5 missing Prometheus alert rules**
    - AIOSShardWorkersDown, AIOSQueueBacklog, AIOSStaleClaims,
      AIOSFleetExhausted, AIOSOutboxApprovalLag.

---

## 🔧 CI/CD Improvements

- **`pyproject.toml`: version bump to 9.4.0**
- Added `[tool.pytest.ini_options]` with asyncio_mode=strict, timeout=30
- Added `pytest-xdist`, `pytest-timeout`, `pytest-cov` to dev dependencies
- Added `[tool.black]` and `[tool.isort]` config sections
- `__init__.py` added to all test subdirectories (chaos, e2e, integration, etc.)

---

## 🔒 Security Documentation

- **`SECURITY_FIX.md`**: credential rotation checklist, data isolation docs,
  API key management, rate limiting details.

---

## 📋 Known Remaining Issues (Non-blocking)

- 13 test failures in `test_platforms_profiles.py` — race condition with
  shared `_PLATFORMS` global dict between tests. Individual runs pass.
- `StarletteDeprecationWarning` on `httpx` with `starlette.testclient` —
  migration to `httpx2` requires rewriting sync tests to async (deferred).
- Dependabot PRs (11 open) — will merge in next sprint.
