"""Unit tests for AIOS v11.16.0 features: dynamic auto-throttling, retention maintenance engine, and snapshot auto-pruning."""

from __future__ import annotations

import time
from pathlib import Path

from aios_core.agent_memory_system import AgentMemorySystem, MemoryEntry, MemoryType
from aios_core.retention import RetentionMaintenanceEngine
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import EnergyAwareScheduler, RollingEnergyBudget


def test_v11_16_auto_throttling():
    """Test dynamic policy auto-throttling on high energy budget pressure."""
    engine = SubstrateConvergenceEngine()
    engine.register_substrate("gpu_high", latency_base_ms=10.0, energy_cost_per_unit=5.0, capacity=10)
    engine.register_substrate("cpu_low", latency_base_ms=10.0, energy_cost_per_unit=1.0, capacity=10)

    budget = RollingEnergyBudget(limit=10.0, window_seconds=3600.0)
    scheduler = EnergyAwareScheduler(engine=engine, energy_budget=budget, policy="ai_optimized")

    scheduler.configure_throttle(enabled=True, threshold=0.5)
    assert scheduler.auto_throttle_enabled is True
    assert scheduler.throttle_threshold == 0.5

    task = {"id": "t1", "category": "general", "compute_units": 1}

    # Low pressure (0.0) -> uses requested policy (ai_optimized)
    plan1 = scheduler.plan(task, policy="ai_optimized")
    assert plan1["policy"] == "ai_optimized"
    assert plan1["throttled"] is False

    # Increase spend to 6.0 / 10.0 = pressure 0.6 >= threshold 0.5
    budget.record(6.0)
    assert budget.pressure() == 0.6

    # High pressure -> auto-throttles to min_energy
    plan2 = scheduler.plan(task, policy="ai_optimized")
    assert plan2["policy"] == "min_energy"
    assert plan2["requested_policy"] == "ai_optimized"
    assert plan2["effective_policy"] == "min_energy"
    assert plan2["throttled"] is True


def test_v11_16_retention_maintenance_engine():
    """Test unified background retention maintenance cycle across subsystems."""
    engine = SubstrateConvergenceEngine()
    engine.register_substrate("s1", latency_base_ms=10.0, energy_cost_per_unit=1.0, capacity=10)

    scheduler = EnergyAwareScheduler(engine=engine)
    memory = AgentMemorySystem()

    # Fill history in all three
    engine.execute_substrate_task({"category": "general", "compute_units": 1})
    scheduler.dispatch({"category": "general", "compute_units": 1})

    memory._archive.append(
        MemoryEntry(
            memory_id="m1",
            memory_type=MemoryType.EPISODIC,
            platform="test",
            action="act",
            result="success",
            created_at=time.time() - 10000.0,
        )
    )

    maint = RetentionMaintenanceEngine(engine=engine, scheduler=scheduler, memory_system=memory)
    report = maint.run_maintenance_cycle(
        keep_last_history=0,
        keep_last_dispatches=0,
        keep_last_archive=0,
        older_than_seconds=0.1,
    )

    assert "total_records_purged" in report
    assert maint.last_run == report


def test_v11_16_snapshot_auto_prune(tmp_path: Path):
    """Test pruning rotated snapshot files by retention count and age."""
    mem = AgentMemorySystem()
    snap = tmp_path / "memory.json"

    # Create 4 rotations
    for _ in range(4):
        mem.save(str(snap), keep_rotated=4)

    existing = AgentMemorySystem.list_snapshot_files(str(snap))
    assert len(existing) >= 2

    # Prune keeping max 2 rotations
    report = AgentMemorySystem.prune_rotated_snapshots(str(snap), max_age_days=30.0, keep_last=2)
    assert "pruned_count" in report
    assert report["pruned_count"] >= 1
