"""Knowledge graph — product/seller relationship storage and querying.

Provides:
- Triple storage (subject → predicate → object)
- Product → Seller → Platform relationships
- Price history → Product connections
- Neighborhood queries (find related products)
- Path queries (find connection paths between entities)
- Inference rules (infer new relationships from existing ones)

Lightweight in-memory graph — no external database required.
Suitable for offline/embedded deployment on Android devices.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RelationType(Enum):
    """Types of relationships in the knowledge graph."""

    SOLD_BY = "sold_by"              # Product → Seller
    LISTED_ON = "listed_on"          # Product → Platform
    SAME_PRODUCT = "same_product"    # Product ↔ Product (cross-platform)
    COMPETES_WITH = "competes_with"  # Seller ↔ Seller
    PRICE_OF = "price_of"            # Price → Product
    CATEGORY_OF = "category_of"      # Category → Product
    BRAND_OF = "brand_of"            # Brand → Product
    LOCATED_IN = "located_in"        # Seller → City
    PREFERRED_OVER = "preferred_over"  # Product → Product (user preference)
    INFERRED = "inferred"            # Auto-inferred relationship


@dataclass
class Triple:
    """A knowledge graph triple (subject → predicate → object)."""

    subject: str
    predicate: str
    object: str
    weight: float = 1.0        # Confidence/weight (0.0 to 1.0)
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "manual"     # Where this triple came from

    def to_dict(self) -> dict[str, Any]:
        """Serialize triple to dict."""
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "weight": round(self.weight, 4),
            "source": self.source,
        }


@dataclass
class EntityInfo:
    """Information about an entity in the graph."""

    entity_id: str
    type: str = "unknown"       # "product", "seller", "platform", "category", "city"
    properties: dict[str, Any] = field(default_factory=dict)
    outgoing_count: int = 0     # Number of outgoing relations
    incoming_count: int = 0     # Number of incoming relations

    @property
    def popularity(self) -> int:
        """Popularity score (total connections)."""
        return self.outgoing_count + self.incoming_count


@dataclass
class PathResult:
    """Result of a path query between two entities."""

    start: str
    end: str
    path: list[str]             # Sequence of entity IDs
    relations: list[str]        # Sequence of predicates
    length: int                 # Number of hops
    total_weight: float         # Sum of weights along path
    confidence: float           # Product of weights along path


class KnowledgeGraph:
    """In-memory knowledge graph for product/seller relationships.

    Provides:
    - add_triple() / remove_triple() — graph mutation
    - find_related() — neighborhood query (find entities connected to a given entity)
    - find_path() — shortest path between two entities
    - infer() — apply inference rules to derive new relationships
    - stats() — graph statistics (entity count, triple count, density)
    """

    def __init__(self, db: Any | None = None) -> None:
        """Initialize KnowledgeGraph.

        Args:
            db: Optional Database instance (kept for compatibility, not used in memory-only mode).
        """
        self._db = db  # Stored for compatibility, but in-memory only for now
        self._triples: list[Triple] = []
        self._outgoing: dict[str, list[Triple]] = defaultdict(list)  # subject → triples
        self._incoming: dict[str, list[Triple]] = defaultdict(list)   # object → triples
        self._entities: dict[str, EntityInfo] = {}
        self._inferred: set[str] = set()  # Set of inferred triple IDs

    def _triple_id(self, triple: Triple) -> str:
        """Generate unique ID for a triple."""
        return f"{triple.subject}|{triple.predicate}|{triple.object}"

    def add_triple(self, triple: Triple) -> None:
        """Add a triple to the knowledge graph.

        Args:
            triple: Triple to add.
        """
        tid = self._triple_id(triple)
        # Check for duplicates
        existing = [t for t in self._outgoing[triple.subject]
                    if self._triple_id(t) == tid]
        if existing:
            # Update weight if duplicate
            existing[0].weight = max(existing[0].weight, triple.weight)
            existing[0].metadata.update(triple.metadata)
            return

        self._triples.append(triple)
        self._outgoing[triple.subject].append(triple)
        self._incoming[triple.object].append(triple)

        # Register entities
        for entity_id in (triple.subject, triple.object):
            if entity_id not in self._entities:
                self._entities[entity_id] = EntityInfo(entity_id=entity_id)

        # Update counts
        self._entities[triple.subject].outgoing_count += 1
        self._entities[triple.object].incoming_count += 1

    def add_node(
        self,
        label: str = "",
        node_type: str = "concept",
        properties: dict[str, Any] | None = None,
        node_id: str | None = None,
    ) -> dict[str, Any]:
        """Add a node (entity) to the graph — API-compatible method.

        Args:
            label: Node label (used as display name and as entity ID if node_id not set).
            node_type: Node type ("concept", "product", "seller", etc.).
            properties: Optional properties dict.
            node_id: Explicit node ID (overrides label-based ID).

        Returns:
            Dict with node info.
        """
        nid = node_id or label or f"node_{len(self._entities)}"
        self.set_entity_type(nid, node_type)
        # Always update label property on upsert
        self.set_entity_property(nid, "label", label)
        if properties:
            for k, v in properties.items():
                self.set_entity_property(nid, k, v)
        entity = self._entities.get(nid)
        if entity:
            return {
                "id": nid,
                "label": label,
                "type": node_type,
                "properties": properties or entity.properties,
                "created": True,
            }
        return {"id": nid, "label": label, "type": node_type, "created": True}

    def add_relation(
        self,
        source_id: str = "",
        target_id: str = "",
        relation: str = "",
        properties: dict[str, Any] | None = None,
        weight: float = 1.0,
        subject: str | None = None,
        predicate: str | None = None,
        object: str | None = None,
        source: str = "manual",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a relation (edge) between two nodes — API-compatible method.

        Supports both API-style (source_id, target_id, relation) and
        graph-style (subject, predicate, object) parameters.

        Args:
            source_id: Source node (used as subject if subject not provided).
            target_id: Target node (used as object if object not provided).
            relation: Relation type (used as predicate if predicate not provided).
            properties: Optional edge properties (stored in metadata).
            weight: Edge weight/confidence.
            subject: Direct subject (overrides source_id).
            predicate: Direct predicate (overrides relation).
            object: Direct object (overrides target_id).
            source: Source of this relation.
            metadata: Optional metadata.

        Returns:
            Dict with edge info.
        """
        s = subject or source_id
        p = predicate or relation
        o = object or target_id

        meta = metadata or properties or {}
        triple = Triple(
            subject=s,
            predicate=p,
            object=o,
            weight=weight,
            source=source,
            metadata=meta,
        )
        self.add_triple(triple)
        result = triple.to_dict()
        # Add API-compatible aliases
        result["source_id"] = s
        result["source"] = s
        result["target_id"] = o
        result["target"] = o
        result["relation"] = p
        return result

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        """Get a node (entity) by ID — API-compatible method.

        Args:
            node_id: Entity ID to retrieve.

        Returns:
            Dict with node info, or None if not found.
        """
        entity = self._entities.get(node_id)
        if not entity:
            return None
        return {
            "id": entity.entity_id,
            "label": entity.properties.get("label", entity.entity_id),
            "type": entity.type,
            "properties": entity.properties,
            "outgoing": entity.outgoing_count,
            "incoming": entity.incoming_count,
            "popularity": entity.popularity,
        }

    def find_nodes(
        self,
        label: str | None = None,
        node_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Find nodes matching criteria — API-compatible method.

        Args:
            label: Filter by label (partial match).
            node_type: Filter by type.
            limit: Maximum results.

        Returns:
            List of node dicts.
        """
        results = []
        for entity in self._entities.values():
            if node_type and entity.type != node_type:
                continue
            if label and label not in entity.entity_id:
                continue
            results.append(self.get_node(entity.entity_id))
            if len(results) >= limit:
                break
        return results

    def count_nodes(self) -> int:
        """Count total number of nodes in the graph.

        Returns:
            Number of nodes/entities.
        """
        return len(self._entities)

    def related(
        self,
        entity_id: str,
        relation: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get related entities as edge dicts — API-compatible method.

        Args:
            entity_id: Central entity.
            relation: Optional relation filter.

        Returns:
            List of dicts with source, target, relation, weight keys.
        """
        triples = self.find_related(entity_id, relation, "both", 100)
        results = []
        for t in triples:
            results.append({
                "source": t.subject,
                "target": t.object,
                "relation": t.predicate,
                "weight": t.weight,
            })
        return results

    def neighbors(
        self,
        node_id: str = "",
        relation: str | None = None,
        depth: int = 1,
    ) -> list[dict[str, Any]]:
        """Get neighbors of a node — API-compatible method.

        Args:
            node_id: Central entity.
            relation: Filter by relation type.
            depth: Search depth (1 = direct, 2 = 2 hops, etc.).

        Returns:
            List of neighbor dicts.
        """
        if depth == 1:
            neighbor_ids = self.find_neighbors(node_id, relation, "both", 100)
            return [self.get_node(nid) for nid in neighbor_ids if self.get_node(nid)]
        else:
            # Multi-hop: BFS
            visited = {node_id}
            frontier = [node_id]
            for d in range(depth):
                next_frontier = []
                for nid in frontier:
                    new_neighbors = self.find_neighbors(nid, relation, "both", 100)
                    for nn in new_neighbors:
                        if nn not in visited:
                            visited.add(nn)
                            next_frontier.append(nn)
                frontier = next_frontier
            # Exclude the original node
            return [self.get_node(nid) for nid in visited if nid != node_id and self.get_node(nid)]

    def path(self, source: str, target: str) -> list[dict[str, Any]]:
        """Find path between two nodes — API-compatible method.

        Args:
            source: Source entity.
            target: Target entity.

        Returns:
            List of edge dicts with source, target, relation keys, or empty list.
        """
        result = self.find_path(source, target)
        if result and result.path and len(result.path) > 1:
            # Convert path to list of edge dicts
            edges = []
            for i in range(len(result.path) - 1):
                edges.append({
                    "source": result.path[i],
                    "target": result.path[i + 1],
                    "relation": result.relations[i] if i < len(result.relations) else "",
                    "weight": 1.0,
                })
            return edges
        return []

    def set_entity_type(self, entity_id: str, type: str) -> None:
        """Set the type of an entity.

        Args:
            entity_id: Entity ID.
            type: Entity type ("product", "seller", "platform", etc.).
        """
        if entity_id in self._entities:
            self._entities[entity_id].type = type
        else:
            self._entities[entity_id] = EntityInfo(entity_id=entity_id, type=type)

    def set_entity_property(self, entity_id: str, key: str, value: Any) -> None:
        """Set a property on an entity.

        Args:
            entity_id: Entity ID.
            key: Property key.
            value: Property value.
        """
        if entity_id not in self._entities:
            self._entities[entity_id] = EntityInfo(entity_id=entity_id)
        self._entities[entity_id].properties[key] = value

    def remove_triple(self, subject: str, predicate: str, object: str) -> bool:
        """Remove a triple from the graph.

        Args:
            subject: Subject entity.
            predicate: Predicate.
            object: Object entity.

        Returns:
            True if triple was found and removed.
        """
        tid = f"{subject}|{predicate}|{object}"

        new_outgoing = [t for t in self._outgoing[subject] if self._triple_id(t) != tid]
        removed = len(self._outgoing[subject]) - len(new_outgoing)
        self._outgoing[subject] = new_outgoing

        new_incoming = [t for t in self._incoming[object] if self._triple_id(t) != tid]
        self._incoming[object] = new_incoming

        self._triples = [t for t in self._triples if self._triple_id(t) != tid]

        if subject in self._entities:
            self._entities[subject].outgoing_count -= removed
        if object in self._entities:
            self._entities[object].incoming_count -= removed

        return removed > 0

    def find_related(
        self,
        entity_id: str,
        predicate: str | None = None,
        direction: str = "both",
        limit: int = 20,
    ) -> list[Triple]:
        """Find entities related to a given entity.

        Args:
            entity_id: Central entity.
            predicate: Filter by predicate type (None = all).
            direction: "outgoing", "incoming", or "both".
            limit: Maximum results.

        Returns:
            List of related Triple instances.
        """
        results: list[Triple] = []

        if direction in ("outgoing", "both"):
            for triple in self._outgoing.get(entity_id, []):
                if predicate and triple.predicate != predicate:
                    continue
                results.append(triple)

        if direction in ("incoming", "both"):
            for triple in self._incoming.get(entity_id, []):
                if predicate and triple.predicate != predicate:
                    continue
                results.append(triple)

        results.sort(key=lambda t: -t.weight)
        return results[:limit]

    def find_neighbors(
        self,
        entity_id: str,
        predicate: str | None = None,
        direction: str = "both",
        limit: int = 20,
    ) -> list[str]:
        """Find neighboring entities (IDs only).

        Args:
            entity_id: Central entity.
            predicate: Filter by predicate.
            direction: "outgoing", "incoming", or "both".
            limit: Maximum neighbors.

        Returns:
            List of neighboring entity IDs.
        """
        triples = self.find_related(entity_id, predicate, direction, limit)
        neighbors: list[str] = []
        for t in triples:
            if t.subject != entity_id and t.subject not in neighbors:
                neighbors.append(t.subject)
            if t.object != entity_id and t.object not in neighbors:
                neighbors.append(t.object)
        return neighbors[:limit]

    def find_path(
        self,
        start: str,
        end: str,
        max_depth: int = 6,
        predicate: str | None = None,
    ) -> PathResult | None:
        """Find shortest path between two entities (BFS).

        Args:
            start: Starting entity.
            end: Target entity.
            max_depth: Maximum search depth.
            predicate: Filter edges by predicate.

        Returns:
            PathResult or None if no path found.
        """
        if start not in self._entities or end not in self._entities:
            return None

        visited: set[str] = {start}
        queue: list[tuple[str, list[str], list[str], float, float]] = [
            (start, [start], [], 0.0, 1.0)
        ]

        while queue:
            current, path, relations, total_weight, confidence = queue.pop(0)

            if len(path) > max_depth:
                continue

            for triple in self._outgoing.get(current, []) + self._incoming.get(current, []):
                if predicate and triple.predicate != predicate:
                    continue

                neighbor = triple.object if triple.subject == current else triple.subject
                if neighbor in visited:
                    continue

                visited.add(neighbor)
                new_path = path + [neighbor]
                new_relations = relations + [triple.predicate]
                new_total = total_weight + triple.weight
                new_conf = confidence * triple.weight

                if neighbor == end:
                    return PathResult(
                        start=start,
                        end=end,
                        path=new_path,
                        relations=new_relations,
                        length=len(new_path) - 1,
                        total_weight=round(new_total, 4),
                        confidence=round(new_conf, 4),
                    )

                queue.append((neighbor, new_path, new_relations, new_total, new_conf))

        return None

    def infer(self, rules: list[tuple[str, str, str, str]] | None = None) -> int:
        """Apply inference rules to derive new relationships.

        Args:
            rules: Custom inference rules as (pred1, pred2, inferred_pred, direction) tuples.

        Returns:
            Number of new inferred triples.
        """
        if rules is None:
            rules = [
                ("sold_by", "located_in", "located_in", "chain"),
                ("same_product", "listed_on", "listed_on", "chain"),
                ("same_product", "sold_by", "sold_by", "chain"),
                ("same_product", "price_of", "price_of", "chain"),
                ("same_product", "category_of", "category_of", "chain"),
            ]

        inferred_count = 0

        for pred1, pred2, inferred_pred, direction in rules:
            for t1 in self._triples:
                if t1.predicate != pred1:
                    continue
                for t2 in self._outgoing.get(t1.object, []):
                    if t2.predicate != pred2:
                        continue
                    inferred_triple = Triple(
                        subject=t1.subject,
                        predicate=inferred_pred,
                        object=t2.object,
                        weight=t1.weight * t2.weight,
                        source="inferred",
                        metadata={
                            "inferred_from": [
                                t1.to_dict(),
                                t2.to_dict(),
                            ],
                        },
                    )

                    tid = self._triple_id(inferred_triple)
                    if tid not in self._inferred:
                        self._inferred.add(tid)
                        self.add_triple(inferred_triple)
                        inferred_count += 1

        return inferred_count

    def get_entity(self, entity_id: str) -> EntityInfo | None:
        """Get entity information.

        Args:
            entity_id: Entity ID.

        Returns:
            EntityInfo or None.
        """
        return self._entities.get(entity_id)

    def get_entities_by_type(self, type: str) -> list[EntityInfo]:
        """Get all entities of a given type.

        Args:
            type: Entity type.

        Returns:
            List of EntityInfo with matching type.
        """
        return [e for e in self._entities.values() if e.type == type]

    def stats(self) -> dict[str, Any]:
        """Compute graph statistics.

        Returns:
            Dict with entity_count, triple_count, density, avg_degree.
        """
        n_entities = len(self._entities)
        n_triples = len(self._triples)
        n_inferred = len(self._inferred)

        avg_out = sum(e.outgoing_count for e in self._entities.values()) / n_entities if n_entities else 0
        avg_in = sum(e.incoming_count for e in self._entities.values()) / n_entities if n_entities else 0

        max_possible = n_entities * (n_entities - 1) if n_entities > 1 else 0
        density = n_triples / max_possible if max_possible > 0 else 0.0

        pred_counts: dict[str, int] = defaultdict(int)
        for t in self._triples:
            pred_counts[t.predicate] += 1

        type_counts: dict[str, int] = defaultdict(int)
        for e in self._entities.values():
            type_counts[e.type] += 1

        return {
            "entities": n_entities,
            "nodes": n_entities,           # Alias for API compatibility
            "edges": n_triples,            # Alias for API compatibility
            "triples": n_triples,
            "inferred_triples": n_inferred,
            "density": round(density, 6),
            "avg_outgoing_degree": round(avg_out, 2),
            "avg_incoming_degree": round(avg_in, 2),
            "predicate_distribution": dict(pred_counts),
            "type_distribution": dict(type_counts),
        }

    def export_triples(self) -> list[dict[str, Any]]:
        """Export all triples as dicts.

        Returns:
            List of triple dicts.
        """
        return [t.to_dict() for t in self._triples]

    def clear(self) -> None:
        """Clear the entire graph."""
        self._triples.clear()
        self._outgoing.clear()
        self._incoming.clear()
        self._entities.clear()
        self._inferred.clear()
