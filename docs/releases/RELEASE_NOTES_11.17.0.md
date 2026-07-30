# AIOS v11.17.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Forecast Metrics Export (`EnergyAwareScheduler.export_forecast_metrics`)
- Translates batch forecast simulations into Prometheus gauge metrics dict (`aios_forecast_tasks_total`, `aios_forecast_affordable_tasks`, `aios_forecast_projected_energy`, `aios_forecast_window_limit`).

### 2. Policy A/B Auto-Tuner (`recommend_optimal_policy` & `auto_tune_policy`)
- `recommend_optimal_policy(tasks_sample)` evaluates recent dispatches or sample task workloads across all scheduling policies and recommends the optimal energy-saving choice.
- `auto_tune_policy(tasks_sample)` dynamically applies the recommended policy.

### 3. Advanced Memory Health Telemetry (`AgentMemorySystem.memory_health_report`)
- `memory_health_report()` computes fragmentation ratio, average entry strength, archive pressure score (0..100), and composite memory vitality score (0..100).

---

## Test Suite Status
- **4348 passed, 0 failed**
