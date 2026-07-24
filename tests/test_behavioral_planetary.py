import pytest
from aios_core.planetary_federation import PlanetaryMeshOrchestrator

def test_planetary_routing_optimal_latency():
    orchestrator = PlanetaryMeshOrchestrator()
    # Task strictly requires < 10ms latency
    task = {"id": "task_ultra_fast", "payload": "trading"}
    
    route = orchestrator.route_planetary_task(task, max_allowed_latency_ms=10.0)
    
    assert route["assigned_node_id"] == "earth_eu_1"
    assert route["estimated_latency_ms"] <= 10.0
    assert route["node_type"] == "terrestrial"

def test_planetary_routing_deep_space_tolerance():
    orchestrator = PlanetaryMeshOrchestrator()
    # Task tolerates 2000ms latency, could go to lunar_edge
    # but the orchestrator takes the first eligible. Let's force only lunar to be eligible.
    orchestrator.nodes["earth_eu_1"].status = "offline"
    orchestrator.nodes["earth_us_east"].status = "offline"
    orchestrator.nodes["starlink_leo_74"].status = "offline"
    
    task = {"id": "task_lunar_science", "payload": "analyze_rocks"}
    route = orchestrator.route_planetary_task(task, max_allowed_latency_ms=2000.0)
    
    assert route["assigned_node_id"] == "lunar_gateway_edge"
    assert route["node_type"] == "lunar_edge"
    
    stats = orchestrator.stats()
    assert stats["reachable_nodes"] == 1
    assert stats["total_routed_tasks"] == 1

def test_planetary_routing_fallback():
    orchestrator = PlanetaryMeshOrchestrator()
    # Requesting impossibly low latency (1ms), lower than any node
    task = {"id": "task_impossible"}
    route = orchestrator.route_planetary_task(task, max_allowed_latency_ms=0.5)
    
    # It should fallback to the minimum latency node available
    assert route["assigned_node_id"] == "earth_eu_1"
    assert route["estimated_latency_ms"] == 2.0
