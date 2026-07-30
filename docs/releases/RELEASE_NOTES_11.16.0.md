# AIOS v11.16.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Dynamic Policy Auto-Throttling (`EnergyAwareScheduler`)
- `EnergyAwareScheduler.configure_throttle(enabled, threshold)` enables dynamic routing policy auto-throttling.
- When energy budget pressure reaches or exceeds `threshold` (default `0.8`), dispatches automatically downgrade from high-energy policies (`ai_optimized`, `balanced`, `min_latency`) to `min_energy` to prevent budget exhaustion violations.

### 2. Unified Retention Maintenance Engine (`RetentionMaintenanceEngine`)
- Centralised retention maintenance engine in `aios_core/retention.py`.
- `run_maintenance_cycle()` executes background cleanup across Substrate Engine history, Scheduler dispatches, and Memory Archive in a single call.

### 3. Snapshot Auto-Pruning (`AgentMemorySystem.prune_rotated_snapshots`)
- `prune_rotated_snapshots(path, max_age_days, keep_last)` automatically cleans up rotated snapshot backups exceeding age or depth limits.

---

## Test Suite Status
- **4345 passed, 0 failed**
