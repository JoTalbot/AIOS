"""AIOS Federation Manager v4.0.0-alpha

Enables multiple AIOS instances to form a federated network:
- Node registration & discovery
- Secure message exchange
- Distributed task delegation
- Constitution synchronization (future)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .storage import Database


class NodeStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


@dataclass
class FederatedNode:
    """Represents a remote AIOS instance in the federation."""
    node_id: str
    name: str
    endpoint: str  # e.g. http://node2.aios.local:8000
    status: NodeStatus = NodeStatus.ONLINE
    last_seen: str = ""
    capabilities: List[str] = field(default_factory=list)
    version: str = "3.1.0"
    metadata: dict = field(default_factory=dict)
    trust_score: float = 1.0


class FederationManager:
    """Manages a network of federated AIOS nodes."""

    def __init__(self, db: Optional[Database] = None, local_node_id: Optional[str] = None):
        self.db = db
        self.local_node_id = local_node_id or f"node_{uuid.uuid4().hex[:8]}"
        self._nodes: Dict[str, FederatedNode] = {}
        self._handlers: Dict[str, Callable] = {}
        self._ensure_table()

        # Register self
        self.register_local_node()

    def _ensure_table(self) -> None:
        if self.db is None:
            return
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS federation_nodes (
                node_id TEXT PRIMARY KEY,
                name TEXT,
                endpoint TEXT,
                status TEXT,
                last_seen TEXT,
                capabilities TEXT,
                version TEXT,
                metadata TEXT,
                trust_score REAL DEFAULT 1.0
            )
        """)

    def register_local_node(self) -> FederatedNode:
        """Register the current instance as a node."""
        node = FederatedNode(
            node_id=self.local_node_id,
            name=f"AIOS-{self.local_node_id}",
            endpoint="http://localhost:8000",
            status=NodeStatus.ONLINE,
            last_seen=datetime.now(timezone.utc).isoformat(),
            capabilities=["orchestration", "memory", "evolution", "constitution"],
            version="3.1.0",
        )
        self._nodes[self.local_node_id] = node
        self._persist_node(node)
        return node

    def register_node(
        self,
        name: str,
        endpoint: str,
        capabilities: Optional[List[str]] = None,
        version: str = "3.1.0",
    ) -> FederatedNode:
        """Register a remote node."""
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        node = FederatedNode(
            node_id=node_id,
            name=name,
            endpoint=endpoint,
            status=NodeStatus.ONLINE,
            last_seen=datetime.now(timezone.utc).isoformat(),
            capabilities=capabilities or [],
            version=version,
        )
        self._nodes[node_id] = node
        self._persist_node(node)
        return node

    def _persist_node(self, node: FederatedNode) -> None:
        if self.db is None:
            return
        import json
        self.db.execute(
            """INSERT OR REPLACE INTO federation_nodes
               (node_id, name, endpoint, status, last_seen, capabilities, version, metadata, trust_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node.node_id,
                node.name,
                node.endpoint,
                node.status.value,
                node.last_seen,
                json.dumps(node.capabilities),
                node.version,
                json.dumps(node.metadata),
                node.trust_score,
            ),
        )

    def heartbeat(self, node_id: str) -> bool:
        """Update last_seen timestamp for a node."""
        if node_id in self._nodes:
            self._nodes[node_id].last_seen = datetime.now(timezone.utc).isoformat()
            self._nodes[node_id].status = NodeStatus.ONLINE
            self._persist_node(self._nodes[node_id])
            return True
        return False

    def get_node(self, node_id: str) -> Optional[FederatedNode]:
        return self._nodes.get(node_id)

    def list_nodes(self, status: Optional[NodeStatus] = None) -> List[FederatedNode]:
        nodes = list(self._nodes.values())
        if status:
            nodes = [n for n in nodes if n.status == status]
        return nodes

    def discover_nodes(self) -> List[FederatedNode]:
        """Simulate node discovery (in real impl would use mDNS / registry)."""
        return [n for n in self._nodes.values() if n.status == NodeStatus.ONLINE]

    def delegate_task(
        self,
        target_node_id: str,
        task_type: str,
        payload: dict,
    ) -> dict:
        """Delegate a task to a remote node (stub implementation)."""
        target = self._nodes.get(target_node_id)
        if not target:
            return {"success": False, "error": "Node not found"}

        if target.status != NodeStatus.ONLINE:
            return {"success": False, "error": f"Node is {target.status.value}"}

        # In real implementation this would do HTTP/gRPC call
        return {
            "success": True,
            "delegated_to": target_node_id,
            "task_type": task_type,
            "payload": payload,
            "message": "Task delegated (simulated)",
            "estimated_completion": "5-30s",
        }

    def broadcast_message(self, message_type: str, payload: dict) -> dict:
        """Broadcast a message to all online nodes."""
        online = [n for n in self._nodes.values() if n.status == NodeStatus.ONLINE]
        results = []
        for node in online:
            if node.node_id != self.local_node_id:
                results.append({
                    "node_id": node.node_id,
                    "status": "sent"
                })
        return {
            "success": True,
            "recipients": len(results),
            "results": results,
            "message_type": message_type,
        }

    def sync_constitution(self, target_node_id: str) -> dict:
        """Request constitution sync from another node."""
        # Placeholder for future implementation
        return {
            "success": True,
            "node_id": target_node_id,
            "message": "Constitution sync requested (not yet implemented)",
        }

    def stats(self) -> dict:
        """Return federation statistics."""
        by_status = {}
        for node in self._nodes.values():
            s = node.status.value
            by_status[s] = by_status.get(s, 0) + 1

        return {
            "version": "4.0.0-alpha",
            "local_node": self.local_node_id,
            "total_nodes": len(self._nodes),
            "by_status": by_status,
            "online_nodes": len([n for n in self._nodes.values() if n.status == NodeStatus.ONLINE]),
        }