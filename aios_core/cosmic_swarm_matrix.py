"""Cosmic Scale Swarm Matrix for AIOS Horizon 8.0.

Provides light-speed delay compensated asynchronous state propagation,
holographic distributed memory state encoding, self-assembling galactic mesh
node topology, inter-node signal routing, and self-healing diagnostics.
"""

import hashlib
import math
import time
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["CosmicSwarmMatrix"]


class CosmicSwarmMatrix:
    """Inter-Stellar Cosmic Swarm Matrix with Holographic State Persistence.

    Models light-speed communication delays between cosmic nodes, maintains
    holographic distributed memory shards, self-assembles mesh topology,
    routes inter-node signals with delay compensation, and self-heals
    offline nodes.
    """

    def __init__(self, default_light_speed_km_per_s: float = 299792.458):
        """Initialize CosmicSwarmMatrix."""
        self.cosmic_nodes: Dict[str, dict[str, Any]] = {}
        self.holographic_shards: Dict[str, dict[str, Any]] = {}
        self._light_speed = default_light_speed_km_per_s
        self._signal_log: List[dict[str, Any]] = []
        self._healing_attempts: int = 0
        self._healing_successes: int = 0

        # Bootstrap default nodes
        self.register_cosmic_node("sol_earth_hub", light_delay_seconds=0.0)
        self.register_cosmic_node(
            "sol_mars_outpost", light_delay_seconds=780.0
        )  # ~13 min
        self.register_cosmic_node(
            "proxima_centauri_node", light_delay_seconds=133800000.0
        )  # ~4.24 ly

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def register_cosmic_node(
        self,
        node_id: str,
        light_delay_seconds: float,
        node_type: str = "relay",
        capacity: float = 1e12,
    ) -> dict[str, Any]:
        """Register inter-stellar node in cosmic mesh topology."""
        record = {
            "node_id": node_id,
            "node_type": node_type,
            "light_delay_seconds": light_delay_seconds,
            "light_delay_km": round(light_delay_seconds * self._light_speed, 3),
            "registered_at": time.time(),
            "status": "active",
            "holographic_sync_status": "synced",
            "capacity": capacity,
            "load": 0.0,
            "health": 1.0,
            "connections": [],
        }
        self.cosmic_nodes[node_id] = record
        # Auto-connect to existing nodes within reachable distance
        for other_id, other in self.cosmic_nodes.items():
            if other_id != node_id:
                combined_delay = (
                    record["light_delay_seconds"]
                    + other["light_delay_seconds"]
                )
                # Nodes within 30-minute round-trip can auto-connect
                if combined_delay * 2 < 1800:
                    record["connections"].append(other_id)
                    other["connections"].append(node_id)
        return record

    def deregister_cosmic_node(self, node_id: str) -> bool:
        """Remove a node from the cosmic mesh."""
        if node_id not in self.cosmic_nodes:
            return False
        # Remove from all other nodes' connection lists
        for other_id, other in self.cosmic_nodes.items():
            if node_id in other.get("connections", []):
                other["connections"].remove(node_id)
        self.cosmic_nodes.pop(node_id)
        return True

    def get_node(self, node_id: str) -> Optional[dict[str, Any]]:
        """Retrieve node info by ID."""
        return self.cosmic_nodes.get(node_id)

    def update_node_health(self, node_id: str, health: float) -> bool:
        """Update health score (0.0–1.0) for a cosmic node."""
        node = self.cosmic_nodes.get(node_id)
        if node is None:
            return False
        node["health"] = max(0.0, min(1.0, health))
        if health < 0.3:
            node["status"] = "degraded"
        elif health < 0.7:
            node["status"] = "warning"
        else:
            node["status"] = "active"
        return True

    # ------------------------------------------------------------------
    # Holographic state storage
    # ------------------------------------------------------------------

    def store_holographic_state(
        self,
        shard_key: str,
        state_payload: dict[str, Any],
        target_nodes: List[str] | None = None,
        redundancy_factor: int = 3,
    ) -> dict[str, Any]:
        """Encode state into holographic distributed memory shards.

        The shard is replicated across *redundancy_factor* active nodes
        (or *target_nodes* if specified) for fault tolerance.
        """
        payload_str = str(state_payload)
        shard_id = f"holo_{hashlib.sha256(shard_key.encode('utf-8')).hexdigest()[:12]}"

        # Select replication targets
        if target_nodes:
            nodes = [
                n for n in target_nodes
                if n in self.cosmic_nodes and self.cosmic_nodes[n]["status"] == "active"
            ]
        else:
            nodes = [
                nid
                for nid, info in self.cosmic_nodes.items()
                if info["status"] == "active"
            ]

        # Apply redundancy factor
        replicated = nodes[:redundancy_factor] if len(nodes) >= redundancy_factor else nodes

        # Compute payload hash for integrity verification
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()[:16]

        shard_record = {
            "shard_id": shard_id,
            "shard_key": shard_key,
            "payload_hash": payload_hash,
            "redundancy_count": len(replicated),
            "replicated_nodes": replicated,
            "redundancy_factor": redundancy_factor,
            "stored_at": time.time(),
            "payload_size_bytes": len(payload_str),
            "sync_status": "distributed" if replicated else "local_only",
        }

        self.holographic_shards[shard_id] = shard_record
        # Update node loads
        for nid in replicated:
            self.cosmic_nodes[nid]["load"] += len(payload_str) / self.cosmic_nodes[nid]["capacity"]

        return shard_record

    def retrieve_holographic_state(
        self, shard_key: str, source_node: str | None = None
    ) -> Optional[dict[str, Any]]:
        """Retrieve holographic shard by key, preferring nearest node."""
        shard_id = f"holo_{hashlib.sha256(shard_key.encode('utf-8')).hexdigest()[:12]}"
        shard = self.holographic_shards.get(shard_id)
        if shard is None:
            return None

        # Choose nearest available replica
        available_nodes = [
            n for n in shard["replicated_nodes"]
            if n in self.cosmic_nodes and self.cosmic_nodes[n]["status"] == "active"
        ]
        if not available_nodes:
            return {"shard": shard, "retrieval_status": "unavailable"}

        if source_node and source_node in available_nodes:
            nearest = source_node
        else:
            # Pick the node with lowest light delay
            nearest = min(
                available_nodes,
                key=lambda n: self.cosmic_nodes[n]["light_delay_seconds"],
            )

        retrieval_delay = self.cosmic_nodes[nearest]["light_delay_seconds"]
        return {
            "shard": shard,
            "retrieval_status": "available",
            "source_node": nearest,
            "retrieval_delay_seconds": retrieval_delay,
        }

    # ------------------------------------------------------------------
    # Inter-node signal routing
    # ------------------------------------------------------------------

    def route_signal(
        self,
        source_node: str,
        target_node: str,
        signal_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Route a signal between cosmic nodes with delay compensation.

        Computes the shortest path through connected nodes and estimates
        total propagation delay.
        """
        if source_node not in self.cosmic_nodes or target_node not in self.cosmic_nodes:
            return {
                "success": False,
                "error": "Source or target node not registered",
            }

        # Find shortest path via BFS on connection graph
        path = self._find_shortest_path(source_node, target_node)
        if path is None:
            return {
                "success": False,
                "error": f"No path from {source_node} to {target_node}",
            }

        # Compute cumulative delay
        total_delay = 0.0
        for i in range(len(path) - 1):
            n1 = self.cosmic_nodes[path[i]]
            n2 = self.cosmic_nodes[path[i + 1]]
            # Delay is the max of the two nodes' delays (inter-node)
            segment_delay = max(
                n1["light_delay_seconds"], n2["light_delay_seconds"]
            )
            total_delay += segment_delay

        signal_id = f"sig_{hashlib.sha256(str(signal_payload).encode()).hexdigest()[:8]}"

        record = {
            "signal_id": signal_id,
            "source": source_node,
            "target": target_node,
            "path": path,
            "total_propagation_delay_seconds": round(total_delay, 3),
            "path_hops": len(path) - 1,
            "payload_size": len(str(signal_payload)),
            "timestamp": time.time(),
            "success": True,
        }
        self._signal_log.append(record)
        return record

    def _find_shortest_path(
        self, source: str, target: str
    ) -> Optional[List[str]]:
        """BFS shortest path through node connection graph."""
        if source == target:
            return [source]
        visited = {source}
        queue: List[Tuple[str, List[str]]] = [(source, [source])]
        while queue:
            current, path = queue.pop(0)
            connections = self.cosmic_nodes[current].get("connections", [])
            for neighbor in connections:
                if neighbor == target:
                    return path + [neighbor]
                if neighbor not in visited and neighbor in self.cosmic_nodes:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None

    # ------------------------------------------------------------------
    # Self-healing diagnostics
    # ------------------------------------------------------------------

    def diagnose_mesh(self) -> dict[str, Any]:
        """Run self-diagnostic on mesh health, connectivity, and shard integrity."""
        active = sum(
            1 for n in self.cosmic_nodes.values() if n["status"] == "active"
        )
        degraded = sum(
            1 for n in self.cosmic_nodes.values() if n["status"] != "active"
        )
        avg_health = (
            sum(n["health"] for n in self.cosmic_nodes.values())
            / max(1, len(self.cosmic_nodes))
        )
        connectivity = (
            sum(len(n.get("connections", [])) for n in self.cosmic_nodes.values())
            / max(1, len(self.cosmic_nodes))
        )
        # Shard integrity: check all replicated nodes are active
        degraded_shards = 0
        for shard in self.holographic_shards.values():
            active_replicas = sum(
                1
                for n in shard["replicated_nodes"]
                if n in self.cosmic_nodes and self.cosmic_nodes[n]["status"] == "active"
            )
            if active_replicas < shard["redundancy_factor"]:
                degraded_shards += 1

        return {
            "total_nodes": len(self.cosmic_nodes),
            "active_nodes": active,
            "degraded_nodes": degraded,
            "average_health": round(avg_health, 3),
            "average_connectivity": round(connectivity, 2),
            "total_shards": len(self.holographic_shards),
            "degraded_shards": degraded_shards,
            "mesh_status": "healthy" if degraded == 0 and degraded_shards == 0 else "degraded",
            "signals_routed": len(self._signal_log),
        }

    def auto_heal(self) -> dict[str, Any]:
        """Attempt self-healing of degraded nodes and under-replicated shards."""
        healed_nodes = 0
        healed_shards = 0

        # Attempt to restore degraded nodes
        for node_id, info in self.cosmic_nodes.items():
            if info["status"] != "active" and info["health"] > 0.5:
                info["status"] = "active"
                info["holographic_sync_status"] = "syncing"
                healed_nodes += 1
                self._healing_successes += 1
            self._healing_attempts += 1

        # Re-replicate under-replicated shards
        for shard_id, shard in self.holographic_shards.items():
            active_replicas = [
                n for n in shard["replicated_nodes"]
                if n in self.cosmic_nodes and self.cosmic_nodes[n]["status"] == "active"
            ]
            if len(active_replicas) < shard["redundancy_factor"]:
                # Add new active nodes to fill redundancy
                available = [
                    nid
                    for nid, info in self.cosmic_nodes.items()
                    if info["status"] == "active" and nid not in shard["replicated_nodes"]
                ]
                needed = shard["redundancy_factor"] - len(active_replicas)
                new_nodes = available[:needed]
                shard["replicated_nodes"].extend(new_nodes)
                shard["redundancy_count"] = len(shard["replicated_nodes"])
                if new_nodes:
                    healed_shards += 1

        return {
            "healed_nodes": healed_nodes,
            "healed_shards": healed_shards,
            "healing_attempts": self._healing_attempts,
            "healing_successes": self._healing_successes,
        }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return statistics dict."""
        return {
            "registered_cosmic_nodes": len(self.cosmic_nodes),
            "holographic_shards_stored": len(self.holographic_shards),
            "signals_routed": len(self._signal_log),
            "healing_attempts": self._healing_attempts,
            "healing_successes": self._healing_successes,
            "interstellar_reach": "Sol-Proxima Centauri Federation",
        }
