# AIOS v11.21.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Adaptive Substrate Self-Healing Engine (`AdaptiveSelfHealingSubstrateEngine`)
- Added `AdaptiveSelfHealingSubstrateEngine` in `aios_core/self_healing.py`.
- Monitors substrate health, latency, and failure rate anomalies via `AnomalyDetector`.
- Automatically executes self-healing actions: capacity reduction or non-performing substrate deactivation.

### 2. REST API & SDK Self-Healing Integration
- Exposed `POST /api/substrate/self-healing/run` (guarded with `confirm: true`).
- Added `run_self_healing()` method to Developer Python SDK (`sdk/aios_sdk.py`).

---

## Test Suite Status
- **4361 passed, 0 failed**
