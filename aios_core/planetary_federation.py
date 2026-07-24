"""Planetary Mesh & Space Edge Orchestration Engine for AIOS Horizon 6.0.

Provides multi-sovereignty terrestrial, satellite orbital mesh, and Lunar/Edge node discovery,
delay-tolerant task routing (DTN), and planetary mesh fault recovery.
"""

import time
import uuid
import math
from typing import Any, Dict, List, Optional


class BundleProtocol:
    """Implements Delay-Tolerant Networking (DTN) Bundle Protocol for deep space links."""
    def __init__(self):
        self.bundles = {}
        
    def encapsulate(self, data: Any, destination: str, ttl_hours: float = 24.0) -> Dict[str, Any]:
        bundle_id = str(uuid.uuid4())
        bundle = {
            "id": bundle_id,
            "payload": data,
            "destination": destination,
            "created_at": time.time(),
            "expires_at": time.time() + (ttl_hours * 3600),
            "status": "queued"
        }
        self.bundles[bundle_id] = bundle
        return bundle
        
    def expire_bundles(self):
        now = time.time()
        expired = [b_id for b_id, b in self.bundles.items() if b["expires_at"] < now]
        for b_id in expired:
            self.bundles[b_id]["status"] = "expired"
            
    def get_bundle(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        return self.bundles.get(bundle_id)


class PlanetaryMeshNode:
    """A Node in the Planetary Mesh network (Terrestrial, Orbital LEO/GEO, or Deep Space/Edge)."""

    def __init__(
        self,
        node_id: str,
        location_type: str = "terrestrial",
        latency_to_earth_ms: float = 5.0,
        bandwidth_mbps: float = 1000.0,
        energy_capacity_wh: float = 10000.0
    ):
        """Initialize PlanetaryMeshNode."""
        self.node_id = node_id
        self.location_type = location_type  # "terrestrial", "orbital_leo", "lunar_edge", "deep_space"
        self.latency_to_earth_ms = latency_to_earth_ms
        self.bandwidth_mbps = bandwidth_mbps
        self.energy_capacity_wh = energy_capacity_wh
        self.energy_consumed_wh = 0.0
        self.status = "online"
        self.active_tasks: List[str] = []

    def is_reachable(self) -> bool:
        """Execute is reachable."""
        # Deep space nodes might have high latency but are reachable if online
        return self.status == "online" and self.energy_consumed_wh < self.energy_capacity_wh
        
    def consume_energy(self, compute_hours: float, transmission_mb: float):
        """Simulate energy drain based on computation and transmission (for space edge nodes)."""
        compute_cost = compute_hours * 50.0  # 50W
        transmission_cost = transmission_mb * 0.1  # 0.1Wh per MB
        self.energy_consumed_wh += compute_cost + transmission_cost
        
    def recharge(self, solar_hours: float):
        """Simulate solar array recharge."""
        charge = solar_hours * 200.0  # 200W solar array
        self.energy_consumed_wh = max(0.0, self.energy_consumed_wh - charge)


class PlanetaryMeshOrchestrator:
    """Planetary Mesh Orchestration Engine with Delay-Tolerant Routing."""

    def __init__(self):
        """Initialize PlanetaryMeshOrchestrator."""
        self.nodes: Dict[str, PlanetaryMeshNode] = {}
        self.routed_tasks: List[Dict[str, Any]] = []
        self.dtn = BundleProtocol()

        # Default mesh nodes
        self.register_node("earth_eu_1", "terrestrial", latency_to_earth_ms=2.0, bandwidth_mbps=10000.0)
        self.register_node("earth_us_east", "terrestrial", latency_to_earth_ms=12.0, bandwidth_mbps=10000.0)
        self.register_node("starlink_leo_74", "orbital_leo", latency_to_earth_ms=25.0, bandwidth_mbps=500.0)
        self.register_node("lunar_gateway_edge", "lunar_edge", latency_to_earth_ms=1300.0, bandwidth_mbps=20.0, energy_capacity_wh=5000.0)
        self.register_node("mars_perseverance", "deep_space", latency_to_earth_ms=840000.0, bandwidth_mbps=2.0, energy_capacity_wh=2000.0)

    def register_node(
        self, node_id: str, location_type: str, latency_to_earth_ms: float, 
        bandwidth_mbps: float = 1000.0, energy_capacity_wh: float = 10000.0
    ) -> PlanetaryMeshNode:
        """Register a new planetary mesh node."""
        node = PlanetaryMeshNode(node_id, location_type, latency_to_earth_ms, bandwidth_mbps, energy_capacity_wh)
        self.nodes[node_id] = node
        return node
        
    def _calculate_route_cost(self, node: PlanetaryMeshNode, payload_size_mb: float) -> float:
        """Calculate custom routing cost factoring latency and transmission time."""
        transmission_time_ms = (payload_size_mb * 8 / node.bandwidth_mbps) * 1000
        total_latency = node.latency_to_earth_ms + transmission_time_ms
        
        # Penalize nodes that are low on energy
        energy_penalty = 1.0
        if node.energy_capacity_wh > 0:
            energy_ratio = node.energy_consumed_wh / node.energy_capacity_wh
            if energy_ratio > 0.8:
                energy_penalty = 5.0
                
        return total_latency * energy_penalty

    def route_planetary_task(
        self, task: Dict[str, Any], max_allowed_latency_ms: float = 100.0, payload_size_mb: float = 1.0
    ) -> Dict[str, Any]:
        """Find the optimal planetary node based on task latency budget, location, and node availability."""
        start_time = time.time()
        task_id = task.get("id", f"p_task_{len(self.routed_tasks)}")
        
        # Determine if we need Delay Tolerant Networking (DTN)
        if max_allowed_latency_ms > 10000:
            bundle = self.dtn.encapsulate(task, "deep_space_broadcast")
            task["dtn_bundle_id"] = bundle["id"]

        eligible_nodes = [
            n for n in self.nodes.values()
            if n.is_reachable() and n.latency_to_earth_ms <= max_allowed_latency_ms
        ]

        if not eligible_nodes:
            # Fallback to terrestrial minimum latency node if constrained
            eligible_nodes = sorted(
                [n for n in self.nodes.values() if n.is_reachable()],
                key=lambda x: self._calculate_route_cost(x, payload_size_mb)
            )

        # Ensure we have at least one node
        if not eligible_nodes:
            return {"error": "No reachable nodes across entire planetary mesh"}

        # Select node with minimum cost
        selected_node = sorted(eligible_nodes, key=lambda n: self._calculate_route_cost(n, payload_size_mb))[0]
        
        # Simulate energy drain for non-terrestrial nodes
        if selected_node.location_type != "terrestrial":
            selected_node.consume_energy(compute_hours=0.01, transmission_mb=payload_size_mb)

        selected_node.active_tasks.append(task_id)

        route_record = {
            "task_id": task_id,
            "assigned_node_id": selected_node.node_id,
            "node_type": selected_node.location_type,
            "estimated_latency_ms": selected_node.latency_to_earth_ms,
            "transmission_time_ms": (payload_size_mb * 8 / selected_node.bandwidth_mbps) * 1000,
            "routing_time_ms": round((time.time() - start_time) * 1000.0, 3),
            "dtn_used": "dtn_bundle_id" in task,
            "timestamp": time.time(),
        }

        self.routed_tasks.append(route_record)
        return route_record
        
    def orbital_sync(self):
        """Simulate orbital window synchronizations and DTN bundle expirations."""
        self.dtn.expire_bundles()
        # Recharge nodes with solar exposure
        for node in self.nodes.values():
            if node.location_type in ["orbital_leo", "lunar_edge"]:
                node.recharge(solar_hours=1.0)

    def stats(self) -> Dict[str, Any]:
        """Return statistics dict."""
        return {
            "total_planetary_nodes": len(self.nodes),
            "reachable_nodes": sum(1 for n in self.nodes.values() if n.is_reachable()),
            "total_routed_tasks": len(self.routed_tasks),
            "active_dtn_bundles": len([b for b in self.dtn.bundles.values() if b["status"] == "queued"]),
            "node_distribution": {
                loc: sum(1 for n in self.nodes.values() if n.location_type == loc)
                for loc in ("terrestrial", "orbital_leo", "lunar_edge", "deep_space")
            },
            "energy_critical_nodes": sum(1 for n in self.nodes.values() if n.energy_capacity_wh > 0 and (n.energy_consumed_wh / n.energy_capacity_wh) > 0.8)
        }

class QuantumLinkManager:
    """Manages instantaneous quantum entanglement links for critical high-priority tasks."""
    
    def __init__(self):
        self.entangled_pairs = set()
        self.decoherence_threshold_ms = 50.0
        
    def establish_link(self, node_a: str, node_b: str) -> bool:
        """Attempt to establish a quantum entangled link."""
        pair = tuple(sorted([node_a, node_b]))
        self.entangled_pairs.add(pair)
        return True
        
    def transmit_instant(self, node_a: str, node_b: str, payload_size_mb: float) -> bool:
        """Transmit data instantly if link is active, consuming the entanglement."""
        pair = tuple(sorted([node_a, node_b]))
        if pair in self.entangled_pairs:
            # Consume pair
            self.entangled_pairs.remove(pair)
            return True
        return False
        
    def stats(self) -> Dict[str, Any]:
        return {"active_entangled_pairs": len(self.entangled_pairs)}
