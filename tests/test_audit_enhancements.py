"""Unit tests for audit enhancements and code quality refactoring (2026-07-30)."""

from __future__ import annotations

import time
from typing import Any

import pytest

from aios_core.agent_memory_system import AgentMemorySystem
from aios_core.metrics_exporter import HistogramConfig, MetricsExporter
from aios_core.retention import plan_retention_purge
from aios_core.substrate_energy_scheduler import RollingEnergyBudget


class DummyObjectWithTimestamp:
    def __init__(self, ts: float):
        self.timestamp = ts


class DummyObjectWithCreatedAt:
    def __init__(self, created_at: float):
        self.created_at = created_at


class DummyObjectInvalidTS:
    def __init__(self, ts: Any):
        self.timestamp = ts


def test_retention_planner_object_fallbacks():
    """Test plan_retention_purge with objects having timestamp, created_at, or invalid ts."""
    now = time.time()
    records = [
        DummyObjectWithTimestamp(now - 100),
        DummyObjectWithCreatedAt(now - 50),
        {"created_at": now - 10},
        DummyObjectInvalidTS("invalid"),
    ]

    # Purge older than 30 seconds
    _cutoff, _protected, removed = plan_retention_purge(records, older_than_seconds=30)
    assert 0 in removed  # ts 100s ago is older than 30s -> removed
    assert 1 in removed  # ts 50s ago is older than 30s -> removed
    assert 2 not in removed  # created_at 10s ago is newer than 30s cutoff
    assert 3 in removed  # invalid timestamp falls back to 0.0, which is < cutoff


def test_metrics_exporter_histogram_cumulative_export():
    """Test MetricsExporter histogram export produces correct cumulative bucket counts."""
    exporter = MetricsExporter()
    exporter.configure_histogram(HistogramConfig("request_duration_seconds", buckets=[0.1, 0.5, 1.0]))

    exporter.observe_histogram("request_duration_seconds", 0.05)
    exporter.observe_histogram("request_duration_seconds", 0.2)
    exporter.observe_histogram("request_duration_seconds", 0.8)

    text = exporter.export()
    # Bucket <=0.1 has 1 item (0.05)
    assert 'request_duration_seconds_bucket{le="0.1"} 1' in text
    # Bucket <=0.5 has 2 items (0.05, 0.2)
    assert 'request_duration_seconds_bucket{le="0.5"} 2' in text
    # Bucket <=1.0 has 3 items (0.05, 0.2, 0.8)
    assert 'request_duration_seconds_bucket{le="1.0"} 3' in text
    # +Inf has 3 items
    assert 'request_duration_seconds_bucket{le="+Inf"} 3' in text


def test_rolling_energy_budget_edge_cases():
    """Test RollingEnergyBudget pressure calculations and edge cases."""
    budget = RollingEnergyBudget(limit=100.0, window_seconds=60.0)
    assert budget.spent() == 0.0
    assert budget.remaining() == 100.0
    assert budget.pressure() == 0.0
    assert budget.can_afford(100.0) is True
    assert budget.can_afford(100.1) is False

    budget.record(50.0)
    assert budget.spent() == 50.0
    assert budget.remaining() == 50.0
    assert budget.pressure() == 0.5

    # Test pressure exceeding 1.0
    budget.record(60.0)
    assert budget.spent() == 110.0
    assert budget.remaining() == 0.0
    assert pytest.approx(budget.pressure(), 0.01) == 1.1


def test_agent_memory_system_list_snapshot_files(tmp_path):
    """Test listing snapshot files with rotation depth gap tolerance."""
    mem = AgentMemorySystem()
    snap_path = tmp_path / "memory.json"
    mem.save(str(snap_path), keep_rotated=3)
    mem.save(str(snap_path), keep_rotated=3)

    files = AgentMemorySystem.list_snapshot_files(str(snap_path))
    assert len(files) >= 2
    rotations = [f["rotation"] for f in files]
    assert 0 in rotations  # live file
    assert 1 in rotations  # rotated file 1
