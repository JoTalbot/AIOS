# AIOS v11.18.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Multi-Tenant Energy Budget Allocation (`MultiTenantBudgetAllocator`)
- `MultiTenantBudgetAllocator` in `aios_core/multitenancy.py` manages tenant-level rolling energy budgets alongside a global energy cap.
- Enforces quota affordability (`can_afford`) and tracks tenant spend with aggregate reporting (`tenant_energy_report`).

### 2. Swarm Workload Balancing (`SwarmWorkloadBalancer`)
- `SwarmWorkloadBalancer` in `aios_core/agent_swarm.py` distributes task batches across active swarm agents matching capabilities, load, and reputation.
- Integrates with `EnergyAwareScheduler` to route assigned tasks through energy-aware substrate policies.

---

## Test Suite Status
- **4350 passed, 0 failed**
