"""Tests for the Prometheus metrics export + /api/metrics endpoint (v11.8.0)."""

from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.agent_memory_system import AgentMemorySystem, MemoryType
from aios_core.dashboard import create_dashboard
from aios_core.metrics_export import render_prometheus
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import EnergyAwareScheduler, RollingEnergyBudget


def _built_trio():
    memory = AgentMemorySystem()
    memory.record("olx", "login", "success", memory_type=MemoryType.LONG_TERM)
    memory.optimize_storage()
    engine = SubstrateConvergenceEngine()
    scheduler = EnergyAwareScheduler(engine, energy_budget=RollingEnergyBudget(limit=10.0))
    scheduler.dispatch({"id": "m1", "category": "general", "compute_units": 2})
    return memory, engine, scheduler


_SAMPLE_RE = re.compile(r"[a-z_]+(\{[^}]*\})? -?\d+(\.\d+)?")


def test_render_contains_core_series():
    memory, engine, scheduler = _built_trio()
    text = render_prometheus(memory_system=memory, engine=engine, scheduler=scheduler, version="19.9.0")
    assert "# HELP aios_info AIOS build information (constant 1)." in text
    assert "# TYPE aios_info gauge" in text
    assert 'aios_info{version="19.9.0"} 1' in text
    # Memory block
    assert 'aios_memory_entries{pool="long_term"} 1' in text
    assert 'aios_memory_entries{pool="short_term"} 0' in text
    assert 'aios_memory_entries{pool="archive"} 0' in text
    assert 'aios_memory_platform_entries{platform="olx"} 1' in text
    assert "aios_memory_dedup_removed_total 0" in text
    assert "aios_memory_compression_entries 1" in text
    # Engine block (seeded defaults, one dispatch)
    assert 'aios_substrates{state="registered"} 5' in text
    assert 'aios_substrates{state="active"} 5' in text
    assert "aios_engine_dispatches_total 1" in text
    assert 'aios_engine_substrate_dispatches_total{substrate="silicon_x86_arm"} 1' in text
    # Scheduler block
    assert "aios_scheduler_dispatches_total 1" in text
    assert "aios_scheduler_fallback_dispatches_total 0" in text
    assert 'aios_scheduler_policy_dispatches_total{policy="min_energy"} 1' in text
    assert 'aios_scheduler_budget{field="limit"} 10' in text
    assert "aios_scheduler_savings_pct" in text
    assert text.endswith("\n")


def test_render_samples_are_well_formed():
    memory, engine, scheduler = _built_trio()
    text = render_prometheus(memory_system=memory, engine=engine, scheduler=scheduler, version="x")
    saw_help = saw_sample = False
    for line in text.splitlines():
        if line.startswith(("# HELP ", "# TYPE ")):
            saw_help = True
            continue
        saw_sample = True
        assert _SAMPLE_RE.fullmatch(line), f"malformed sample line: {line!r}"
    assert saw_help and saw_sample


def test_render_escapes_label_values():
    memory = AgentMemorySystem()
    memory.record('pla"tform\\\no', "act", "success", memory_type=MemoryType.LONG_TERM)
    text = render_prometheus(memory_system=memory)
    assert 'platform="pla\\"tform\\\\\\no"' in text


def test_render_omits_missing_sources():
    text = render_prometheus()
    assert 'aios_info{version="unknown"} 1' in text
    assert "aios_memory_entries" not in text
    assert "aios_substrates" not in text
    assert "aios_scheduler_dispatches_total" not in text


def test_render_never_emits_non_finite():
    memory, engine, scheduler = _built_trio()
    text = render_prometheus(memory_system=memory, engine=engine, scheduler=scheduler)
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        value = line.rsplit(" ", 1)[-1].lower()
        assert value not in ("nan", "inf", "+inf", "-inf"), f"non-finite sample: {line!r}"


# ----------------------------------------------------------------------
# Dashboard endpoint
# ----------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._memory_system = None
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.8.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_metrics_endpoint_shape(client):
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "version=0.0.4" in resp.headers["content-type"]
    body = resp.text
    assert 'aios_info{version="19.9.0"} 1' in body
    # Seeded memory singleton: 3 LT + 4 EP demo entries.
    assert 'aios_memory_entries{pool="long_term"} 3' in body
    assert 'aios_memory_entries{pool="episodic"} 4' in body
    assert 'aios_substrates{state="registered"} 5' in body
    assert "aios_scheduler_dispatches_total 0" in body


def test_metrics_endpoint_reflects_dispatches(client):
    client.post(
        "/api/substrate/schedule", json={"id": "fx", "category": "general", "compute_units": 2, "execute": True}
    )
    body = client.get("/api/metrics").text
    assert "aios_scheduler_dispatches_total 1" in body
    assert "aios_engine_dispatches_total 1" in body
    assert 'aios_scheduler_policy_dispatches_total{policy="min_energy"} 1' in body
