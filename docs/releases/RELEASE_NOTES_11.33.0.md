# AIOS v11.33.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. AI Agent Swarm Auto-Scaling & Dynamic Role Allocator (`SwarmAutoScaler`)
- Added `SwarmAutoScaler` in `aios_core/swarm_auto_scaler.py`.
- Dynamically spawns, reassigns, and adjusts swarm agent roles based on pending workload demand.
- REST API: `POST /api/ai/swarm/autoscale`.
- SDK: `ai_autoscale_swarm()`.

---

## Test Suite Status
- **4390 passed, 0 failed**
