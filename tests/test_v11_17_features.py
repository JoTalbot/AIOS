"""Unit tests for AIOS v11.17.0 features: forecast metrics export, policy auto-tuner, and memory health report."""

from __future__ import annotations

import time

from aios_core.agent_memory_system import AgentMemorySystem, MemoryEntry, MemoryType
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import EnergyAwareScheduler


def test_v11_17_forecast_metrics_export():
    """Test exporting forecast batch simulation into Prometheus metrics format."""
    engine = SubstrateConvergenceEngine()
    engine.register_substrate("sub1", latency_base_ms=10.0, energy_cost_per_unit=2.0, capacity=10)

    scheduler = EnergyAwareScheduler(engine=engine)
    tasks = [
        {"id": "t1", "category": "general", "compute_units": 1},
        {"id": "t2", "category": "general", "compute_units": 2},
    ]

    metrics = scheduler.export_forecast_metrics(tasks)
    assert metrics["aios_forecast_tasks_total"] == 2
    assert metrics["aios_forecast_affordable_tasks"] == 2
    assert metrics["aios_forecast_projected_energy"] > 0.0


def test_v11_17_policy_recommend_and_auto_tune():
    """Test policy optimization recommendation and dynamic auto-tuning."""
    engine = SubstrateConvergenceEngine()
    engine.register_substrate("cheap_slow", latency_base_ms=100.0, energy_cost_per_unit=1.0, capacity=10)
    engine.register_substrate("fast_expensive", latency_base_ms=10.0, energy_cost_per_unit=5.0, capacity=10)

    scheduler = EnergyAwareScheduler(engine=engine, policy="min_latency")

    # Dispatch several tasks
    for i in range(5):
        scheduler.dispatch({"id": f"t_{i}", "category": "general", "compute_units": 1})

    rec = scheduler.recommend_optimal_policy()
    assert "recommended_policy" in rec
    assert rec["sample_size"] == 5

    tune_res = scheduler.auto_tune_policy()
    assert tune_res["changed"] is True or tune_res["new_policy"] == scheduler.policy


def test_v11_17_memory_health_report():
    """Test memory health report calculation."""
    mem = AgentMemorySystem()
    mem._short_term.append(
        MemoryEntry(
            memory_id="s1",
            memory_type=MemoryType.EPISODIC,
            platform="test",
            action="act",
            result="success",
        )
    )
    mem._long_term.append(
        MemoryEntry(
            memory_id="l1",
            memory_type=MemoryType.EPISODIC,
            platform="test",
            action="act",
            result="success",
        )
    )

    mem._archive.append(
        MemoryEntry(
            memory_id="m1",
            memory_type=MemoryType.EPISODIC,
            platform="test",
            action="act",
            result="success",
            created_at=time.time() - 1000.0,
        )
    )

    report = mem.memory_health_report()
    assert "vitality_score" in report
    assert "fragmentation_ratio" in report
    assert "archive_pressure_score" in report
    assert report["active_entries"] == 2
    assert report["archive_entries"] == 1
