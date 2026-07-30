# AIOS v11.20.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Developer Python SDK Client Expansion (`sdk/aios_sdk.py`)
- Added async methods to `AIOSClient` and synchronous mirrors to `AIOSClientSync` for all v11.16–v11.19 features:
  - `get_throttle_config()` & `configure_throttle()`
  - `auto_tune_policy()`
  - `get_memory_health()`
  - `prune_snapshots()`
  - `run_retention_maintenance()`

### 2. Complete Official Release Notes & Documentation (`docs/releases/`)
- Created official Markdown release documentation for releases v11.16.0 through v11.20.0 under `docs/releases/`.

---

## Test Suite Status
- **4358 passed, 0 failed**
