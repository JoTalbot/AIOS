"""AIOS Knowledge Graph v3.0.0

Persistent knowledge graph using SQLite. Supports nodes, typed edges,
bidirectional traversal, and basic graph queries.
"""

from __future__ import annotations

from typing import Any, Optional

from .storage import Database

__all__ = ["KnowledgeGraph"]


class KnowledgeGraph:
    """Manages a knowledge graph of concepts, rules, and relationships.

    Nodes and edges are stored in SQLite with indexes for
    efficient traversal and lookup.
    """

    def __init__(self, db: Optional[Database] = None):
        self.db = db

    def add_node(
        self,
        label: str,
        node_type: str = "concept",
        properties: Optional[dict] = None,
        node_id: str | None = None,
    ) -> dict:
        """Add a node to the graph.

        Args:
            label: Human-readable label.
            node_type: Type of node (concept, rule, agent, article, etc.).
            properties: Arbitrary properties dict.
            node_id: Optional specific ID. If None, auto-generated.

        Returns:
            The created node dict.
        """
        nid = node_id or Database.new_id()
        now = Database.now_iso()

        if self.db:
            # Upsert: if node exists, update label and properties
            existing = self.get_node(nid)
            if existing:
                self.db.execute(
                    """UPDATE kg_nodes
                       SET label = ?, node_type = ?, properties = ?, updated_at = ?
                       WHERE id = ?""",
                    (
                        label,
                        node_type,
                        Database.to_json(properties) if properties else None,
                        now,
                        nid,
                    ),
                )
            else:
                self.db.execute(
                    """INSERT INTO kg_nodes (id, node_type, label, properties, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        nid,
                        node_type,
                        label,
                        Database.to_json(properties) if properties else None,
                        now,
                        now,
                    ),
                )

        return {
            "id": nid,
            "label": label,
            "type": node_type,
            "properties": properties or {},
            "created_at": now,
        }

    def get_node(self, node_id: str) -> Optional[dict]:
        """Get a node by ID."""
        if self.db is None:
            return None
        row = self.db.query_one("SELECT * FROM kg_nodes WHERE id = ?", (node_id,))
        if row is None:
            return None
        return self._node_row_to_dict(row)

    def find_nodes(
        self,
        label: str | None = None,
        node_type: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Find nodes by label (partial match) and/or type."""
        if self.db is None:
            return []

        conditions = []
        params: list[Any] = []

        if label:
            conditions.append("label LIKE ?")
            params.append(f"%{label}%")
        if node_type:
            conditions.append("node_type = ?")
            params.append(node_type)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"SELECT * FROM kg_nodes {where} LIMIT ?"
        params.append(limit)

        rows = self.db.query(sql, tuple(params))
        return [self._node_row_to_dict(r) for r in rows]

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        properties: Optional[dict] = None,
        weight: float = 1.0,
        edge_id: str | None = None,
    ) -> dict:
        """Add a directed edge (relation) between two nodes.

        Auto-creates nodes if they don't exist.
        """
        # Auto-create nodes if needed
        if self.db:
            if not self.get_node(source_id):
                self.add_node(source_id, node_type="auto", node_id=source_id)
            if not self.get_node(target_id):
                self.add_node(target_id, node_type="auto", node_id=target_id)

        eid = edge_id or Database.new_id()
        now = Database.now_iso()

        if self.db:
            self.db.execute(
                """INSERT INTO kg_edges (id, source_id, target_id, relation, properties, weight, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    eid,
                    source_id,
                    target_id,
                    relation,
                    Database.to_json(properties) if properties else None,
                    weight,
                    now,
                ),
            )

        return {
            "id": eid,
            "source": source_id,
            "target": target_id,
            "relation": relation,
            "properties": properties or {},
            "weight": weight,
            "created_at": now,
        }

    def related(
        self,
        node_id: str,
        relation: str | None = None,
        direction: str = "both",
        limit: int = 100,
    ) -> list[dict]:
        """Find edges connected to a node.

        Args:
            node_id: The node to find relations for.
            relation: Filter by relation type.
            direction: 'outgoing', 'incoming', or 'both'.
        """
        if self.db is None:
            return []

        where_parts: list[str] = []
        params: list[Any] = []

        if direction == "outgoing":
            where_parts.append("source_id = ?")
            params.append(node_id)
        elif direction == "incoming":
            where_parts.append("target_id = ?")
            params.append(node_id)
        else:  # both
            where_parts.append("(source_id = ? OR target_id = ?)")
            params.extend([node_id, node_id])

        if relation:
            where_parts.append("relation = ?")
            params.append(relation)

        where = "WHERE " + " AND ".join(where_parts)
        sql = f"SELECT * FROM kg_edges {where} LIMIT ?"
        params.append(limit)

        rows = self.db.query(sql, tuple(params))
        return [self._edge_row_to_dict(r) for r in rows]

    def neighbors(
        self,
        node_id: str,
        relation: str | None = None,
        depth: int = 1,
    ) -> list[dict]:
        """Find neighboring nodes (BFS traversal up to depth)."""
        if self.db is None or depth < 1:
            return []

        visited = {node_id}
        current_level = [node_id]
        result_nodes = []

        for _ in range(depth):
            next_level = []
            for nid in current_level:
                edges = self.related(nid, relation=relation, direction="both")
                for edge in edges:
                    other = edge["target"] if edge["source"] == nid else edge["source"]
                    if other not in visited:
                        visited.add(other)
                        next_level.append(other)
                        node = self.get_node(other)
                        if node:
                            result_nodes.append(node)
            current_level = next_level
            if not current_level:
                break

        return result_nodes

    def path(self, source_id: str, target_id: str) -> list[dict]:
        """Find a shortest path between two nodes using BFS. Returns edge list."""
        if self.db is None:
            return []

        if source_id == target_id:
            return []

        visited = {source_id}
        # Queue items: (current_node, path_of_edges)
        from collections import deque

        queue: deque[tuple[str, list[dict]]] = deque()

        # Start: get all edges from source
        start_edges = self.related(source_id, direction="outgoing")
        for edge in start_edges:
            neighbor = edge["target"]
            if neighbor == target_id:
                return [edge]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, [edge]))

        while queue:
            current, path = queue.popleft()
            edges = self.related(current, direction="outgoing")
            for edge in edges:
                neighbor = edge["target"]
                if neighbor in visited:
                    continue
                new_path = path + [edge]
                if neighbor == target_id:
                    return new_path
                visited.add(neighbor)
                queue.append((neighbor, new_path))

        return []  # No path found

    def count_nodes(self) -> int:
        """Execute count nodes."""
        if self.db is None:
            return 0
        return self.db.query_one("SELECT COUNT(*) as cnt FROM kg_nodes")["cnt"]

    def count_edges(self) -> int:
        """Execute count edges."""
        if self.db is None:
            return 0
        return self.db.query_one("SELECT COUNT(*) as cnt FROM kg_edges")["cnt"]

    def stats(self) -> dict:
        """Return statistics dict."""
        if self.db is None:
            return {"nodes": 0, "edges": 0, "storage": "none"}

        type_rows = self.db.query(
            "SELECT node_type, COUNT(*) as cnt FROM kg_nodes GROUP BY node_type"
        )
        rel_rows = self.db.query("SELECT relation, COUNT(*) as cnt FROM kg_edges GROUP BY relation")

        return {
            "nodes": self.count_nodes(),
            "edges": self.count_edges(),
            "by_node_type": {r["node_type"]: r["cnt"] for r in type_rows},
            "by_relation": {r["relation"]: r["cnt"] for r in rel_rows},
            "storage": "sqlite",
        }

    def _node_row_to_dict(self, row: dict) -> dict:
        return {
            "id": row["id"],
            "label": row["label"],
            "type": row["node_type"],
            "properties": (Database.from_json(row["properties"]) if row["properties"] else {}),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _edge_row_to_dict(self, row: dict) -> dict:
        return {
            "id": row["id"],
            "source": row["source_id"],
            "target": row["target_id"],
            "relation": row["relation"],
            "properties": (Database.from_json(row["properties"]) if row["properties"] else {}),
            "weight": row["weight"],
            "created_at": row["created_at"],
        }
