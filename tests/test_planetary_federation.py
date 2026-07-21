"""Tests for Planetary Mesh & Space Edge Orchestration Engine (Horizon 6.0)."""

import pytest
from aios_core.planetary_federation import PlanetaryMeshOrchestrator, PlanetaryMeshNode


def test_planetary_mesh_routing():
    mesh = PlanetaryMeshOrchestrator()

    # Route low-latency terrestrial task (<30ms)
    route_fast = mesh.route_planetary_task({"id": "task_fast", "payload": "realtime_control"}, max_allowed_latency_ms=30.0)
    assert route_fast["assigned_node_id"] in ["earth_eu_1", "earth_us_east", "starlink_leo_74"]
    assert route_fast["estimated_latency_ms"] <= 30.0

    # Route high latency budget task (up to 2000ms) -> eligible for Lunar Edge
    route_space = mesh.route_planetary_task({"id": "task_space", "payload": "lunar_geology_analysis"}, max_allowed_latency_ms=2000.0)
    assert route_space["assigned_node_id"] is not None

    stats = mesh.stats()
    assert stats["total_planetary_nodes"] >= 4
    assert stats["total_routed_tasks"] == 2
