"""Quantum Internet / Quantum Networking for AIOS v10.11.0.

Quantum networking: node management, entanglement
distribution, quantum teleportation, quantum memory,
network topology, and fidelity tracking.

Classes:
    QuantumNetworkNode — single quantum node
    QuantumInternet     — full quantum network
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class QuantumNetworkNode:
    """Quantum network node (backward-compatible)."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.entangled_pairs: dict[str, float] = {}
        self.quantum_memory: dict[str, Any] = {}
        self._qubit_capacity: int = 100
        self._messages_sent: int = 0

    def entangle(self, other_node: str, fidelity: float = 0.95) -> None:
        """Entangle with another node (backward-compatible)."""
        self.entangled_pairs[other_node] = fidelity

    def teleport(self, qubit_state: complex, target: str) -> bool:
        """Teleport qubit (backward-compatible)."""
        fidelity = self.entangled_pairs.get(target, 0.0)
        success = target in self.entangled_pairs and fidelity > 0.8
        if success:
            self._messages_sent += 1
            self.quantum_memory[f"teleported_{self._messages_sent}"] = qubit_state
        return success

    def store_qubit(self, key: str, state: complex, duration_ms: float = 100) -> None:
        """Store a qubit in quantum memory."""
        self.quantum_memory[key] = {
            "state": state,
            "stored_at": time.time(),
            "duration_ms": duration_ms,
        }

    def stats(self) -> dict[str, Any]:
        return {
            "node": self.node_id,
            "entangled_pairs": len(self.entangled_pairs),
            "memory_used": len(self.quantum_memory),
            "messages_sent": self._messages_sent,
        }


class QuantumInternet:
    """Quantum network infrastructure (backward-compatible)."""

    def __init__(self) -> None:
        self.nodes: dict[str, QuantumNetworkNode] = {}
        self.links: list[tuple[str, str]] = []
        self._fidelity_log: list[float] = []

    def add_node(self, node_id: str) -> None:
        """Add node (backward-compatible)."""
        self.nodes[node_id] = QuantumNetworkNode(node_id)

    def create_link(self, node_a: str, node_b: str, fidelity: float = 0.95) -> None:
        """Create quantum link (backward-compatible + fidelity)."""
        self.links.append((node_a, node_b))
        if node_a in self.nodes and node_b in self.nodes:
            self.nodes[node_a].entangle(node_b, fidelity)
            self.nodes[node_b].entangle(node_a, fidelity)
            self._fidelity_log.append(fidelity)

    def route_message(self, source: str, destination: str) -> list[str]:
        """Route a quantum message through the network."""
        if source not in self.nodes or destination not in self.nodes:
            return []
        # Simple shortest path (breadth-first)
        visited: set[str] = {source}
        path: list[str] = [source]
        current = source
        while current != destination:
            neighbors = [
                b for a, b in self.links if a == current and b not in visited
            ] + [a for a, b in self.links if b == current and a not in visited]
            if not neighbors:
                return []
            current = neighbors[0]
            path.append(current)
            visited.add(current)
        return path

    def network_fidelity(self) -> float:
        """Average network fidelity."""
        if not self._fidelity_log:
            return 0.0
        return round(sum(self._fidelity_log) / len(self._fidelity_log), 3)

    def quantum_key_distribution(
        self, node_a: str, node_b: str, key_length: int = 128
    ) -> dict[str, Any]:
        """Distribute a quantum key between two nodes."""
        fidelity = (
            self.nodes[node_a].entangled_pairs.get(node_b, 0.0)
            if node_a in self.nodes
            else 0.0
        )
        success = fidelity > 0.8
        return {
            "source": node_a,
            "destination": node_b,
            "key_length": key_length,
            "fidelity": round(fidelity, 3),
            "success": success,
            "error_rate": round(1 - fidelity, 3) if success else 1.0,
        }

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "nodes": len(self.nodes),
            "links": len(self.links),
            "avg_fidelity": self.network_fidelity(),
        }
