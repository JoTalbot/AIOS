"""Agent memory system — long-term memory for scraping agents.

Provides:
- Short-term memory: recent actions and results (ephemeral, session-based)
- Long-term memory: learned patterns and success/failure rates (persistent)
- Episodic memory: specific scraping session records
- Memory consolidation: summarize short-term into long-term insights
- Memory retrieval: find relevant past experiences for current situations
- Memory decay: reduce influence of old memories over time
- Success pattern extraction: identify what worked best for each platform

Enables agents to learn from past scraping sessions and adapt behavior.
"""

from __future__ import annotations

import math
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MemoryType(Enum):
    """Types of agent memory."""

    SHORT_TERM = "short_term"  # Recent actions (last session)
    LONG_TERM = "long_term"  # Learned patterns (consolidated)
    EPISODIC = "episodic"  # Specific session records
    PROCEDURAL = "procedural"  # Learned procedures/strategies


class MemoryPriority(Enum):
    """Memory importance priority."""

    CRITICAL = "critical"  # Must remember (bans, blocks)
    HIGH = "high"  # Important patterns
    NORMAL = "normal"  # Standard observations
    LOW = "low"  # Background info
    TRIVIAL = "trivial"  # Can decay quickly


@dataclass
class MemoryEntry:
    """A single memory entry."""

    memory_id: str
    memory_type: MemoryType
    platform: str  # "olx", "rozetka", etc.
    action: str  # "collect", "parse", "login", etc.
    result: str  # "success", "failure", "blocked", "banned"
    context: dict[str, Any] = field(default_factory=dict)
    priority: MemoryPriority = MemoryPriority.NORMAL
    confidence: float = 1.0  # How reliable is this memory
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    decay_rate: float = 0.01  # Memory strength decay per day
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def strength(self) -> float:
        """Current memory strength (decays over time)."""
        age_days = (time.time() - self.created_at) / 86400
        strength = self.confidence * math.exp(-self.decay_rate * age_days)
        # Boost strength if frequently accessed
        strength += min(0.3, self.access_count * 0.01)
        return min(1.0, strength)

    @property
    def age_days(self) -> float:
        """Age of this memory in days."""
        return (time.time() - self.created_at) / 86400

    def to_dict(self) -> dict[str, Any]:
        """Serialize memory entry."""
        return {
            "memory_id": self.memory_id,
            "type": self.memory_type.value,
            "platform": self.platform,
            "action": self.action,
            "result": self.result,
            "priority": self.priority.value,
            "strength": round(self.strength, 4),
            "age_days": round(self.age_days, 1),
            "access_count": self.access_count,
            "context": self.context,
        }


@dataclass
class SuccessPattern:
    """A learned success pattern extracted from episodic memories."""

    pattern_id: str
    platform: str
    action: str
    success_rate: float
    avg_latency_ms: float
    avg_items: float
    best_params: dict[str, Any]
    sample_size: int
    confidence: float
    discovered_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize pattern."""
        return {
            "pattern_id": self.pattern_id,
            "platform": self.platform,
            "action": self.action,
            "success_rate": round(self.success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "avg_items": round(self.avg_items, 1),
            "best_params": self.best_params,
            "sample_size": self.sample_size,
            "confidence": round(self.confidence, 4),
        }


class AgentMemorySystem:
    """Agent memory system for learning from past scraping sessions.

    Provides:
    - record() — store a memory entry
    - recall() — retrieve relevant memories
    - consolidate() — summarize short-term into long-term
    - extract_patterns() — find success patterns from episodic data
    - decay() — reduce strength of old memories
    - get_advice() — get advice based on past experiences
    - stats() — memory statistics
    """

    def __init__(
        self,
        max_short_term: int = 100,
        max_long_term: int = 500,
        max_episodic: int = 2000,
        consolidation_interval: float = 3600,
    ) -> None:
        """Initialize AgentMemorySystem.

        Args:
            max_short_term: Max short-term memories.
            max_long_term: Max long-term memories.
            max_episodic: Max episodic memories.
            consolidation_interval: Seconds between auto-consolidation.
        """
        self.max_short_term = max_short_term
        self.max_long_term = max_long_term
        self.max_episodic = max_episodic
        self.consolidation_interval = consolidation_interval
        self._short_term: list[MemoryEntry] = []
        self._long_term: list[MemoryEntry] = []
        self._episodic: list[MemoryEntry] = []
        self._patterns: dict[str, SuccessPattern] = {}
        self._last_consolidation: float = time.time()
        self._counter: int = 0

        # Vector compression state (Agent Memory Optimization, v11.3.0)
        self._compressed: dict[str, Any] = {}  # memory_id -> CompressedVector
        self._vectorizer: Any = None
        self._compressor: Any = None
        self._compression_report: dict[str, Any] = {}

        # Deduplication state (Memory Deduplication Engine, v11.4.0)
        self._dedup_report: dict[str, Any] = {}
        self._dedup_removed_total: int = 0
        # Default duplicate threshold, adjustable by the auto-tuner (v11.9.0)
        self._dedup_threshold: float = 0.92

        # Cold-storage archive (Memory Lifecycle, v11.5.0)
        self._archive: list[MemoryEntry] = []
        self._archive_report: dict[str, Any] = {}

    def _next_id(self) -> str:
        """Generate unique memory ID."""
        self._counter += 1
        return f"mem_{self._counter}"

    def record(
        self,
        platform: str,
        action: str,
        result: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        context: dict[str, Any] | None = None,
        priority: MemoryPriority = MemoryPriority.NORMAL,
        confidence: float = 1.0,
        decay_rate: float = 0.01,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Record a memory entry.

        Args:
            platform: Target platform.
            action: Action performed.
            result: Result of action.
            memory_type: Type of memory.
            context: Additional context (params, errors, etc.).
            priority: Memory priority.
            confidence: Initial confidence.
            decay_rate: Decay rate per day.
            metadata: Optional metadata.

        Returns:
            Recorded MemoryEntry.
        """
        entry = MemoryEntry(
            memory_id=self._next_id(),
            memory_type=memory_type,
            platform=platform,
            action=action,
            result=result,
            context=context or {},
            priority=priority,
            confidence=confidence,
            decay_rate=decay_rate,
            metadata=metadata or {},
        )

        if memory_type == MemoryType.SHORT_TERM:
            self._short_term.append(entry)
            if len(self._short_term) > self.max_short_term:
                self._short_term = self._short_term[-self.max_short_term :]
        elif memory_type == MemoryType.LONG_TERM:
            self._long_term.append(entry)
            if len(self._long_term) > self.max_long_term:
                self._long_term = self._long_term[-self.max_long_term :]
        elif memory_type == MemoryType.EPISODIC:
            self._episodic.append(entry)
            if len(self._episodic) > self.max_episodic:
                self._episodic = self._episodic[-self.max_episodic :]

        return entry

    def record_session(
        self,
        platform: str,
        action: str,
        success: bool,
        latency_ms: float = 0,
        items: int = 0,
        params: dict[str, Any] | None = None,
        errors: list[str] | None = None,
    ) -> MemoryEntry:
        """Record a scraping session result.

        Args:
            platform: Platform name.
            action: Action performed.
            success: Whether session succeeded.
            latency_ms: Session latency.
            items: Items collected.
            params: Parameters used.
            errors: Any errors encountered.

        Returns:
            Recorded episodic MemoryEntry.
        """
        priority = MemoryPriority.CRITICAL if not success else MemoryPriority.NORMAL
        if errors and any("ban" in e.lower() or "block" in e.lower() for e in errors):
            priority = MemoryPriority.CRITICAL

        context = {
            "latency_ms": latency_ms,
            "items": items,
            "params": params or {},
            "errors": errors or [],
            "success": success,
        }

        return self.record(
            platform=platform,
            action=action,
            result="success" if success else "failure",
            memory_type=MemoryType.EPISODIC,
            context=context,
            priority=priority,
            confidence=0.8 if success else 0.6,
            decay_rate=0.005 if success else 0.02,
        )

    def recall(
        self,
        platform: str | None = None,
        action: str | None = None,
        result: str | None = None,
        memory_type: MemoryType | None = None,
        min_strength: float = 0.1,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """Retrieve relevant memories.

        Args:
            platform: Filter by platform.
            action: Filter by action.
            result: Filter by result.
            memory_type: Filter by memory type.
            min_strength: Minimum memory strength threshold.
            limit: Maximum results.

        Returns:
            List of matching MemoryEntry sorted by strength.
        """
        all_memories = []

        pools = []
        if memory_type == MemoryType.SHORT_TERM:
            pools = [self._short_term]
        elif memory_type == MemoryType.LONG_TERM:
            pools = [self._long_term]
        elif memory_type == MemoryType.EPISODIC:
            pools = [self._episodic]
        else:
            pools = [self._short_term, self._long_term, self._episodic]

        for pool in pools:
            for entry in pool:
                if platform and entry.platform != platform:
                    continue
                if action and entry.action != action:
                    continue
                if result and entry.result != result:
                    continue
                if entry.strength < min_strength:
                    continue
                entry.last_accessed = time.time()
                entry.access_count += 1
                all_memories.append(entry)

        # Sort by strength descending
        all_memories.sort(key=lambda m: -m.strength)
        return all_memories[:limit]

    def consolidate(self) -> int:
        """Consolidate short-term and episodic memories into long-term insights.

        Summarizes repeated patterns into long-term memories with higher confidence.

        Returns:
            Number of new long-term memories created.
        """
        consolidated = 0
        now = time.time()

        # Auto-consolidate only if interval elapsed
        if now - self._last_consolidation < self.consolidation_interval:
            return 0

        self._last_consolidation = now

        # Group episodic memories by (platform, action)
        groups: dict[str, list[MemoryEntry]] = defaultdict(list)
        for entry in self._episodic:
            key = f"{entry.platform}:{entry.action}"
            groups[key].append(entry)

        for key, entries in groups.items():
            if len(entries) < 3:
                continue

            platform, action = key.split(":")
            successes = [e for e in entries if e.result == "success"]
            failures = [e for e in entries if e.result == "failure"]

            success_rate = len(successes) / len(entries) if entries else 0

            # Create long-term summary
            summary = MemoryEntry(
                memory_id=self._next_id(),
                memory_type=MemoryType.LONG_TERM,
                platform=platform,
                action=action,
                result="consolidated",
                context={
                    "success_rate": round(success_rate, 4),
                    "total_sessions": len(entries),
                    "success_count": len(successes),
                    "failure_count": len(failures),
                    "avg_latency": sum(e.context.get("latency_ms", 0) for e in entries) / len(entries),
                    "avg_items": sum(e.context.get("items", 0) for e in entries) / len(entries),
                },
                priority=MemoryPriority.HIGH if success_rate > 0.7 else MemoryPriority.NORMAL,
                confidence=min(0.95, 0.5 + len(entries) * 0.05),
                decay_rate=0.001,  # Long-term decays slowly
            )

            self._long_term.append(summary)
            consolidated += 1

        # Trim long-term
        if len(self._long_term) > self.max_long_term:
            # Remove weakest memories
            self._long_term.sort(key=lambda m: -m.strength)
            self._long_term = self._long_term[: self.max_long_term]

        return consolidated

    def extract_patterns(self) -> list[SuccessPattern]:
        """Extract success patterns from episodic memories.

        Identifies parameter configurations that achieved highest success rates.

        Returns:
            List of SuccessPattern with best parameters per (platform, action).
        """
        patterns: list[SuccessPattern] = []

        # Group by (platform, action)
        groups: dict[str, list[MemoryEntry]] = defaultdict(list)
        for entry in self._episodic:
            if entry.result == "success":
                key = f"{entry.platform}:{entry.action}"
                groups[key].append(entry)

        for key, successes in groups.items():
            if len(successes) < 3:
                continue

            platform, action = key.split(":")

            # Find best params (highest items / lowest latency)
            best_entry = max(
                successes,
                key=lambda e: e.context.get("items", 0) / max(1, e.context.get("latency_ms", 1)),
            )

            pattern = SuccessPattern(
                pattern_id=f"pattern_{len(self._patterns)}",
                platform=platform,
                action=action,
                success_rate=len(successes)
                / max(
                    1,
                    len([e for e in self._episodic if e.platform == platform and e.action == action]),
                ),
                avg_latency_ms=sum(e.context.get("latency_ms", 0) for e in successes) / len(successes),
                avg_items=sum(e.context.get("items", 0) for e in successes) / len(successes),
                best_params=best_entry.context.get("params", {}),
                sample_size=len(successes),
                confidence=min(0.9, 0.3 + len(successes) * 0.1),
            )

            self._patterns[pattern.pattern_id] = pattern
            patterns.append(pattern)

        return patterns

    def get_advice(
        self,
        platform: str,
        action: str,
    ) -> dict[str, Any]:
        """Get advice for a scraping action based on past experiences.

        Args:
            platform: Target platform.
            action: Action to get advice for.

        Returns:
            Dict with recommended params, warnings, success_rate.
        """
        # Find relevant long-term memories
        self.recall(platform=platform, action=action, memory_type=MemoryType.LONG_TERM, limit=5)

        # Find relevant patterns
        pattern = None
        for p in self._patterns.values():
            if p.platform == platform and p.action == action:
                pattern = p
                break

        # Check for past failures/blocks
        failures = self.recall(platform=platform, action=action, result="failure", limit=5)

        # Check for past blocks/bans
        blocks = self.recall(platform=platform, result="blocked", limit=5)

        advice: dict[str, Any] = {
            "platform": platform,
            "action": action,
            "recommended_params": pattern.best_params if pattern else {},
            "expected_success_rate": pattern.success_rate if pattern else 0.5,
            "warnings": [],
            "avoid_params": [],
        }

        # Add warnings from failures
        for f in failures[:3]:
            if f.strength > 0.3:
                advice["warnings"].append(f"{f.action} failed on {f.platform}: {f.context.get('errors', ['unknown'])}")

        # Add block/ban warnings
        for b in blocks[:3]:
            advice["warnings"].append(f"⚠️ BLOCK detected on {b.platform}: avoid {b.context.get('params', {})}")

        # Find params that led to failures
        bad_params = []
        for f in failures:
            params = f.context.get("params", {})
            if params:
                bad_params.append(params)

        if bad_params:
            # Find most common bad param values
            advice["avoid_params"] = bad_params[:3]

        return advice

    def decay(self, min_strength: float = 0.05) -> int:
        """Remove memories below minimum strength threshold.

        Args:
            min_strength: Minimum strength to keep.

        Returns:
            Number of memories removed.
        """
        before = len(self._short_term) + len(self._episodic)
        self._short_term = [m for m in self._short_term if m.strength >= min_strength]
        self._episodic = [m for m in self._episodic if m.strength >= min_strength]
        return before - len(self._short_term) - len(self._episodic)

    def clear_short_term(self) -> int:
        """Clear all short-term memories.

        Returns:
            Number of memories cleared.
        """
        count = len(self._short_term)
        self._short_term.clear()
        return count

    # ── Agent Memory Optimization (vector compression, v11.3.0) ─────────

    def _ensure_compressor(self, target_dim: int = 64) -> None:
        """Lazily build text vectoriser + compressor (import guarded).

        Recreates the compressor (keeping the vectorizer) when a different
        ``target_dim`` is requested — e.g. by optimize_storage_adaptive.
        """
        if self._vectorizer is not None and self._compressor is not None:
            if self._compressor.target_dim == target_dim:
                return
            from aios_core.memory_compression import VectorCompressor

            self._compressor = VectorCompressor(target_dim=target_dim)
            self._compressor.fit(self._vectorizer.dim)
            return
        try:
            from aios_core.memory_compression import HashingVectorizer, VectorCompressor
        except ImportError as exc:  # pragma: no cover - numpy is a hard dep
            raise RuntimeError("Vector compression requires aios_core.memory_compression (numpy)") from exc
        self._vectorizer = HashingVectorizer(dim=512)
        self._compressor = VectorCompressor(target_dim=target_dim)
        # fit immediately on the vectoriser width
        self._compressor.fit(self._vectorizer.dim)

    def _entry_text(self, entry: MemoryEntry) -> str:
        """Flatten a memory entry into a vectorisable text."""
        import json as _json

        try:
            ctx = _json.dumps(entry.context, sort_keys=True, ensure_ascii=False)
        except Exception:
            ctx = str(entry.context)
        return f"{entry.platform} {entry.action} {entry.result} {ctx}"

    def optimize_storage(self, target_dim: int = 64) -> dict[str, Any]:
        """Compress long-term + episodic memory contexts into uint8 vectors.

        Keeps raw entries untouched (compressed vectors are an index for
        fast similarity recall), replaces previous index on each call.

        Returns:
            Compression report with byte savings.
        """
        self._ensure_compressor(target_dim)
        self._compressed.clear()

        entries = [*self._long_term, *self._episodic]
        for entry in entries:
            vec = self._vectorizer.vectorize(self._entry_text(entry))
            self._compressed[entry.memory_id] = self._compressor.compress(vec)

        original_bytes = len(entries) * self._vectorizer.dim * 8
        compressed_bytes = sum(cv.byte_size() for cv in self._compressed.values())
        self._compression_report = {
            "entries_compressed": len(entries),
            "source_dim": self._vectorizer.dim,
            "target_dim": target_dim,
            "original_bytes": original_bytes,
            "compressed_bytes": compressed_bytes,
            "ratio": round(original_bytes / compressed_bytes, 2) if compressed_bytes else 0.0,
            "compressed_at": time.time(),
        }
        return dict(self._compression_report)

    def optimize_storage_adaptive(
        self,
        min_overlap: float = 0.8,
        top_k: int = 5,
        dims: list[int] | None = None,
        probes: int = 8,
    ) -> dict[str, Any]:
        """Compress with an adaptively chosen dimension (v11.5.0).

        Probes recall-ranking stability per candidate dim (dense vs
        compressed top-k overlap) via ``AdaptiveTuner`` and stores the
        index at the smallest dim meeting ``min_overlap``. The adaptive
        report persists inside ``compression_stats()["adaptive"]``.

        With fewer than two memories there is nothing to probe — falls
        back to the default 64 dimensions.
        """
        from .memory_compression import AdaptiveTuner

        entries = {e.memory_id: self._entry_text(e) for e in [*self._long_term, *self._episodic]}
        if len(entries) < 2:
            report = self.optimize_storage()
            report["adaptive"] = {
                "selected_dim": 64,
                "scores": {},
                "skipped": "not_enough_entries",
                "entries": len(entries),
            }
            self._compression_report["adaptive"] = report["adaptive"]
            return report

        self._ensure_compressor()  # need the vectorizer for probes
        tuner = AdaptiveTuner(
            self._vectorizer,
            dims=dims,
            min_overlap=min_overlap,
            top_k=top_k,
        )
        selection = tuner.select(entries, probes=probes)
        report = self.optimize_storage(target_dim=selection["selected_dim"])
        report["adaptive"] = selection
        self._compression_report["adaptive"] = selection
        return report

    def recall_compressed(
        self,
        query: str,
        top_k: int = 5,
        pool: str = "long_term",
    ) -> list[MemoryEntry]:
        """Similarity recall entirely in compressed space (JL-preserved).

        Args:
            query: free-form text query.
            top_k: number of memories to return.
            pool: "long_term", "episodic" or "all".

        Returns:
            Top-k memory entries by cosine similarity to the query.
        """
        if not self._compressed:
            self.optimize_storage()
        if not self._compressed:
            return []

        candidates: list[MemoryEntry]
        if pool == "long_term":
            candidates = list(self._long_term)
        elif pool == "episodic":
            candidates = list(self._episodic)
        else:
            candidates = [*self._long_term, *self._episodic]

        qv = self._compressor.compress(self._vectorizer.vectorize(query))
        scored = []
        for entry in candidates:
            cv = self._compressed.get(entry.memory_id)
            if cv is None:
                continue
            scored.append((self._compressor.cosine_similarity(qv, cv), entry))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [entry for _score, entry in scored[: max(0, top_k)]]

    def compression_stats(self) -> dict[str, Any]:
        """Last optimize_storage() report (empty dict if never run)."""
        return dict(self._compression_report)

    # ------------------------------------------------------------------
    # Keyword search (v11.6.0)
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        limit: int = 20,
        pools: str = "all",
    ) -> list[dict[str, Any]]:
        """Token-based keyword search across memory entries (no vectors).

        Score = fraction of query tokens present in the flattened entry
        text (case-insensitive); ties break by entry strength. Entries
        with zero hits are excluded.

        Args:
            query: free-form text.
            limit: max results.
            pools: "all" (short+long+episodic), "short_term", "long_term",
                "episodic" or "archive" (cold storage from v11.5.0).

        Returns:
            [{**entry.to_dict(), "score"}] sorted by score then strength.
        """
        tokens = [t for t in re.split(r"\W+", query.lower()) if t]
        if not tokens:
            return []

        if pools == "short_term":
            candidates = list(self._short_term)
        elif pools == "long_term":
            candidates = list(self._long_term)
        elif pools == "episodic":
            candidates = list(self._episodic)
        elif pools == "archive":
            candidates = list(self._archive)
        else:
            candidates = [*self._short_term, *self._long_term, *self._episodic]

        scored: list[tuple[float, MemoryEntry]] = []
        for entry in candidates:
            text = self._entry_text(entry).lower()
            hits = sum(1 for token in tokens if token in text)
            if hits:
                scored.append((hits / len(tokens), entry))

        scored.sort(key=lambda t: (-t[0], -t[1].strength))
        return [{**entry.to_dict(), "score": round(score, 4)} for score, entry in scored[: max(0, limit)]]

    # ------------------------------------------------------------------
    # Deduplication (Memory Deduplication Engine, v11.4.0)
    # ------------------------------------------------------------------

    def _pool_entries(self, pool: str) -> list[MemoryEntry]:
        """Entries covered by the compressed index for the given pool."""
        if pool == "long_term":
            return list(self._long_term)
        if pool == "episodic":
            return list(self._episodic)
        return [*self._long_term, *self._episodic]

    def _duplicate_groups(
        self,
        threshold: float,
        pool: str,
    ) -> tuple[list[Any], dict[str, MemoryEntry]]:
        """Raw DuplicateGroups + id->entry map for the scanned pool."""
        from .memory_dedup import MemoryDeduplicator

        if not self._compressed:
            self.optimize_storage()
        if not self._compressed:
            return [], {}

        entries = self._pool_entries(pool)
        by_id = {e.memory_id: e for e in entries}
        vectors = {mid: self._compressed[mid] for mid in by_id if mid in self._compressed}
        if len(vectors) < 2:
            return [], by_id

        score = {mid: by_id[mid].strength for mid in vectors}
        deduplicator = MemoryDeduplicator(threshold=threshold)
        groups = deduplicator.find_groups(vectors, self._compressor, score=score)
        return groups, by_id

    def find_duplicates(
        self,
        threshold: float = 0.92,
        pool: str = "all",
    ) -> list[dict[str, Any]]:
        """Detect near-duplicate memories without modifying anything.

        Similarity is measured in compressed space (the index built by
        optimize_storage); pairs with cosine >= threshold are clustered.

        Args:
            threshold: cosine similarity threshold in (0.0, 1.0].
            pool: "long_term", "episodic" or "all".

        Returns:
            Group dicts (representative_id, member_ids, avg_similarity),
            sorted by group size (desc) then representative id.
        """
        groups, _ = self._duplicate_groups(threshold, pool)
        return [g.to_dict() for g in groups]

    def deduplicate(
        self,
        threshold: float = 0.92,
        pool: str = "all",
    ) -> dict[str, Any]:
        """Merge near-duplicate memories into single representatives.

        Merge policy: the strongest entry in each group survives; it
        absorbs the access counts and best confidence of the merged
        members, then the members are removed from the pools and from
        the compressed index.

        Returns:
            Deduplication report (groups found, entries removed, etc.).
        """
        groups, by_id = self._duplicate_groups(threshold, pool)

        removed_ids: set[str] = set()
        merged: list[dict[str, Any]] = []
        for group in groups:
            rep = by_id.get(group.representative_id)
            if rep is None:
                continue
            absorbed = [by_id[mid] for mid in group.absorbed_ids() if mid in by_id]
            rep.access_count += sum(a.access_count for a in absorbed)
            if absorbed:
                rep.confidence = max(rep.confidence, *(a.confidence for a in absorbed))
                rep.last_accessed = max(rep.last_accessed, *(a.last_accessed for a in absorbed))
            removed_ids.update(a.memory_id for a in absorbed)
            merged.append(group.to_dict())

        if removed_ids:
            self._long_term = [e for e in self._long_term if e.memory_id not in removed_ids]
            self._episodic = [e for e in self._episodic if e.memory_id not in removed_ids]
            for mid in removed_ids:
                self._compressed.pop(mid, None)

        self._dedup_removed_total += len(removed_ids)
        self._dedup_report = {
            "groups_found": len(merged),
            "entries_removed": len(removed_ids),
            "removed_ids": sorted(removed_ids),
            "merged": merged,
            "threshold": threshold,
            "pool": pool,
            "deduplicated_at": time.time(),
        }
        return dict(self._dedup_report)

    def preview_dedup(
        self,
        threshold: float | None = None,
        pool: str = "all",
    ) -> dict[str, Any]:
        """Dry-run the dedup merge plan WITHOUT merging anything (v11.10.0).

        Applies the exact merge policy of deduplicate() (strongest entry
        survives; absorbs access counts, best confidence and latest
        access) and reports what WOULD happen: per-group projections and
        post-merge pool counts. With threshold=None the system's (possibly
        tuner-set) default dedup_threshold is used.

        Returns:
            Preview dict: threshold, groups, would_remove, counts_after
            and per-group merge plans with projected representative stats.
        """
        effective = self._dedup_threshold if threshold is None else float(threshold)
        groups, by_id = self._duplicate_groups(effective, pool)

        long_term_ids = {e.memory_id for e in self._long_term}
        episodic_ids = {e.memory_id for e in self._episodic}
        absorbed_lt = absorbed_ep = 0

        plans: list[dict[str, Any]] = []
        for group in groups:
            rep = by_id[group.representative_id]
            absorbed = [by_id[mid] for mid in group.absorbed_ids() if mid in by_id]
            for entry in absorbed:
                if entry.memory_id in long_term_ids:
                    absorbed_lt += 1
                elif entry.memory_id in episodic_ids:
                    absorbed_ep += 1
            plans.append(
                {
                    "representative_id": rep.memory_id,
                    "absorbed_ids": [a.memory_id for a in absorbed],
                    "avg_similarity": round(group.avg_similarity, 4),
                    "projected": {
                        "access_count": rep.access_count + sum(a.access_count for a in absorbed),
                        "confidence": max([rep.confidence, *(a.confidence for a in absorbed)]),
                        "strength": rep.strength,
                    },
                }
            )

        return {
            "dry_run": True,
            "threshold": effective,
            "pool": pool,
            "groups": len(plans),
            "would_remove": absorbed_lt + absorbed_ep,
            "counts_after": {
                "long_term": len(self._long_term) - absorbed_lt,
                "episodic": len(self._episodic) - absorbed_ep,
            },
            "plans": plans,
        }

    def dedup_stats(self) -> dict[str, Any]:
        """Deduplication summary: last report + lifetime removal count."""
        return {
            "removed_total": self._dedup_removed_total,
            "threshold": self._dedup_threshold,
            "last_report": dict(self._dedup_report),
        }

    @property
    def dedup_threshold(self) -> float:
        """Current default near-duplicate threshold (v11.9.0)."""
        return self._dedup_threshold

    # ------------------------------------------------------------------
    # Dedup threshold auto-tuning (v11.9.0)
    # ------------------------------------------------------------------

    def tune_dedup_threshold(
        self,
        pool: str = "all",
        candidates: list[float] | None = None,
        apply: bool = False,
    ) -> dict[str, Any]:
        """Auto-tune the near-duplicate threshold over real signatures.

        Scans candidate thresholds against the compressed index (built
        on demand, exactly like find_duplicates) and recommends the
        cut-off with the best confidence-weighted merge count. With
        ``apply=True`` the recommendation becomes the system's default
        ``dedup_threshold`` (persisted in snapshots) — nothing is merged
        either way, so tuning is always safe to run.

        Args:
            pool: "long_term", "episodic" or "all".
            candidates: thresholds to scan (module default set if None).
            apply: store the recommendation as the new default.

        Returns:
            Tuning report (recommendation, per-candidate stats, applied).
        """
        from .memory_dedup import tune_dedup_threshold

        if not self._compressed:
            self.optimize_storage()
        entries = self._pool_entries(pool)
        by_id = {e.memory_id: e for e in entries}
        vectors = {mid: self._compressed[mid] for mid in by_id if mid in self._compressed}
        score = {mid: by_id[mid].strength for mid in vectors}

        report = tune_dedup_threshold(vectors, self._compressor, score=score, candidates=candidates)
        report["pool"] = pool
        report["applied"] = False
        if apply:
            self._dedup_threshold = report["recommended_threshold"]
            report["applied"] = True
        return report

    # ------------------------------------------------------------------
    # Cold-storage archive (Memory Lifecycle, v11.5.0)
    # ------------------------------------------------------------------

    def archive_dead(
        self,
        min_strength: float = 0.05,
        min_age_days: float = 1.0,
    ) -> dict[str, Any]:
        """Move dead long-term memories into the cold-storage archive.

        An entry is "dead" when its decayed strength is below
        ``min_strength`` AND it is at least ``min_age_days`` old. Archived
        entries leave the active pool AND the compressed index (they no
        longer appear in recall()/recall_compressed()) but stay inspectable
        via ``archived()``. Short-term and episodic pools are untouched —
        archival targets the long-term layer only.

        Returns:
            Archival report (count, ids, thresholds).
        """
        if min_strength < 0:
            raise ValueError("min_strength must be >= 0")
        if min_age_days < 0:
            raise ValueError("min_age_days must be >= 0")

        moved: list[MemoryEntry] = []
        keep: list[MemoryEntry] = []
        for entry in self._long_term:
            if entry.strength < min_strength and entry.age_days >= min_age_days:
                moved.append(entry)
            else:
                keep.append(entry)

        self._long_term = keep
        self._archive.extend(moved)
        for entry in moved:
            self._compressed.pop(entry.memory_id, None)

        self._archive_report = {
            "archived": len(moved),
            "archived_ids": [e.memory_id for e in moved],
            "min_strength": min_strength,
            "min_age_days": min_age_days,
            "archived_at": time.time(),
        }
        return dict(self._archive_report)

    def archive_stats(self) -> dict[str, Any]:
        """Archive summary: lifetime count + last archival report."""
        return {
            "archived_total": len(self._archive),
            "last_report": dict(self._archive_report),
        }

    def preview_archive_dead(
        self,
        min_strength: float = 0.05,
        min_age_days: float = 1.0,
    ) -> dict[str, Any]:
        """Dry-run archive_dead() WITHOUT moving anything (v11.11.0).

        Applies the exact same "dead" criterion (decayed strength below
        ``min_strength`` AND age at least ``min_age_days``) and reports
        what WOULD move to cold storage: ids, per-entry age/strength and
        post-archival pool counts. Mirrors preview_dedup() (v11.10.0) so
        lifecycle operations share one preview pattern.

        Returns:
            Preview dict: thresholds, would_archive, plans, counts_after.
        """
        if min_strength < 0:
            raise ValueError("min_strength must be >= 0")
        if min_age_days < 0:
            raise ValueError("min_age_days must be >= 0")

        dead = [e for e in self._long_term if e.strength < min_strength and e.age_days >= min_age_days]
        return {
            "dry_run": True,
            "min_strength": min_strength,
            "min_age_days": min_age_days,
            "would_archive": len(dead),
            "entries": [
                {
                    "memory_id": e.memory_id,
                    "platform": e.platform,
                    "action": e.action,
                    "strength": round(e.strength, 4),
                    "age_days": round(e.age_days, 2),
                }
                for e in dead
            ],
            "counts_after": {
                "long_term": len(self._long_term) - len(dead),
                "archive": len(self._archive) + len(dead),
            },
        }

    def archived(self, limit: int = 20) -> list[dict[str, Any]]:
        """Most recently archived entries (newest last), serialised."""
        return [e.to_dict() for e in self._archive[-max(0, limit) :]]

    # ------------------------------------------------------------------
    # Persistence (snapshot export/import, v11.6.0)
    # ------------------------------------------------------------------

    #: On-disk snapshot format version (bump on incompatible changes).
    SNAPSHOT_FORMAT = 1

    @staticmethod
    def _entry_snapshot(entry: MemoryEntry) -> dict[str, Any]:
        """Full-fidelity serialisation (unlike to_dict, keeps decay fields)."""
        return {
            "memory_id": entry.memory_id,
            "memory_type": entry.memory_type.value,
            "platform": entry.platform,
            "action": entry.action,
            "result": entry.result,
            "context": entry.context,
            "priority": entry.priority.value,
            "confidence": entry.confidence,
            "created_at": entry.created_at,
            "last_accessed": entry.last_accessed,
            "access_count": entry.access_count,
            "decay_rate": entry.decay_rate,
            "metadata": entry.metadata,
        }

    @staticmethod
    def _entry_from_snapshot(data: dict[str, Any]) -> MemoryEntry:
        return MemoryEntry(
            memory_id=str(data["memory_id"]),
            memory_type=MemoryType(data["memory_type"]),
            platform=str(data["platform"]),
            action=str(data["action"]),
            result=str(data["result"]),
            context=dict(data.get("context") or {}),
            priority=MemoryPriority(data.get("priority", MemoryPriority.NORMAL.value)),
            confidence=float(data.get("confidence", 1.0)),
            created_at=float(data.get("created_at", time.time())),
            last_accessed=float(data.get("last_accessed", time.time())),
            access_count=int(data.get("access_count", 0)),
            decay_rate=float(data.get("decay_rate", 0.01)),
            metadata=dict(data.get("metadata") or {}),
        )

    def snapshot(self) -> dict[str, Any]:
        """Full memory state as a JSON-serialisable dict.

        The compressed vector index is NOT persisted (it is derived state:
        rebuild with optimize_storage() / optimize_storage_adaptive()).
        """
        return {
            "format": self.SNAPSHOT_FORMAT,
            "created_at": time.time(),
            "counter": self._counter,
            "dedup_removed_total": self._dedup_removed_total,
            "dedup_threshold": self._dedup_threshold,
            "pools": {
                "short_term": [self._entry_snapshot(e) for e in self._short_term],
                "long_term": [self._entry_snapshot(e) for e in self._long_term],
                "episodic": [self._entry_snapshot(e) for e in self._episodic],
                "archive": [self._entry_snapshot(e) for e in self._archive],
            },
            "patterns": [p.to_dict() for p in self._patterns.values()],
        }

    def restore(self, data: dict[str, Any]) -> dict[str, Any]:
        """Replace the entire memory state from a snapshot dict.

        The id counter is raised past the largest ``mem_N`` id found, so
        entries recorded after restore can never collide with restored ids.

        Raises:
            ValueError: unsupported or missing snapshot format version.
        """
        if not isinstance(data, dict) or "pools" not in data:
            raise ValueError("not an AgentMemorySystem snapshot (missing 'pools')")
        fmt = data.get("format")
        if fmt != self.SNAPSHOT_FORMAT:
            raise ValueError(f"unsupported snapshot format {fmt!r} (expected {self.SNAPSHOT_FORMAT})")

        pools = data["pools"]
        for name in ("short_term", "long_term", "episodic", "archive"):
            if name not in pools:
                raise ValueError(f"snapshot pools missing '{name}'")

        self._short_term = [self._entry_from_snapshot(e) for e in pools["short_term"]]
        self._long_term = [self._entry_from_snapshot(e) for e in pools["long_term"]]
        self._episodic = [self._entry_from_snapshot(e) for e in pools["episodic"]]
        self._archive = [self._entry_from_snapshot(e) for e in pools["archive"]]

        self._patterns = {}
        for pdata in data.get("patterns", []):
            pattern = SuccessPattern(
                pattern_id=str(pdata["pattern_id"]),
                platform=str(pdata["platform"]),
                action=str(pdata["action"]),
                success_rate=float(pdata["success_rate"]),
                avg_latency_ms=float(pdata["avg_latency_ms"]),
                avg_items=float(pdata["avg_items"]),
                best_params=dict(pdata.get("best_params") or {}),
                sample_size=int(pdata["sample_size"]),
                confidence=float(pdata["confidence"]),
            )
            self._patterns[pattern.pattern_id] = pattern

        # Derived/index state does not survive the restore.
        self._compressed.clear()
        self._compression_report = {}
        self._dedup_report = {}
        self._archive_report = {}
        self._dedup_removed_total = int(data.get("dedup_removed_total", 0))
        tuned = float(data.get("dedup_threshold", 0.92))
        self._dedup_threshold = min(1.0, tuned) if tuned > 0.0 else 0.92

        # Id uniqueness: counter must pass every restored mem_N id.
        max_id = int(data.get("counter", 0))
        for pool in (self._short_term, self._long_term, self._episodic, self._archive):
            for entry in pool:
                match = re.fullmatch(r"mem_(\d+)", entry.memory_id)
                if match:
                    max_id = max(max_id, int(match.group(1)))
        self._counter = max_id

        return {
            "short_term": len(self._short_term),
            "long_term": len(self._long_term),
            "episodic": len(self._episodic),
            "archive": len(self._archive),
            "patterns": len(self._patterns),
        }

    def save(self, path: str) -> dict[str, Any]:
        """Atomically write the snapshot to ``path`` (tmp file + rename)."""
        import json
        from pathlib import Path

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(json.dumps(self.snapshot(), ensure_ascii=False), encoding="utf-8")
        tmp.replace(target)
        return {"saved": str(target)}

    def load(self, path: str) -> dict[str, Any]:
        """Load a snapshot written by :meth:`save` (replaces current state)."""
        import json
        from pathlib import Path

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        report = self.restore(data)
        report["loaded"] = str(path)
        return report

    def diff_snapshot(self, other: dict[str, Any]) -> dict[str, Any]:
        """Compare the LIVE memory state against a snapshot dict (v11.12.0).

        Entry equality uses full-fidelity serialisation (the same
        _entry_snapshot used by save(); derived strength is deliberately
        NOT compared), so only real mutations surface — passive decay
        drift never produces phantom changes.

        Args:
            other: snapshot dict as produced by snapshot()/save().

        Returns:
            Diff dict: added/removed/changed ids per pool, pattern drift,
            pool counts on both sides, metadata drift and an `identical`
            flag.
        Raises:
            ValueError: malformed snapshot structure.
        """
        if not isinstance(other, dict) or "pools" not in other:
            raise ValueError("not an AgentMemorySystem snapshot (missing 'pools')")
        pools = other["pools"]
        if not isinstance(pools, dict):
            raise ValueError("not an AgentMemorySystem snapshot ('pools' must be a dict)")
        for name in ("short_term", "long_term", "episodic", "archive"):
            if name not in pools or not isinstance(pools[name], list):
                raise ValueError(f"snapshot pools missing '{name}'")

        live_pools = {
            "short_term": self._short_term,
            "long_term": self._long_term,
            "episodic": self._episodic,
            "archive": self._archive,
        }
        added: dict[str, list[str]] = {}
        removed: dict[str, list[str]] = {}
        changed: dict[str, list[str]] = {}
        live_totals: dict[str, int] = {}
        snap_totals: dict[str, int] = {}
        for name, entries in live_pools.items():
            live_map = {e.memory_id: self._entry_snapshot(e) for e in entries}
            snap_map = {str(e.get("memory_id")): e for e in pools[name] if isinstance(e, dict)}
            added[name] = sorted(mid for mid in live_map if mid not in snap_map)
            removed[name] = sorted(mid for mid in snap_map if mid not in live_map)
            changed[name] = sorted(mid for mid in live_map if mid in snap_map and live_map[mid] != snap_map[mid])
            live_totals[name] = len(live_map)
            snap_totals[name] = len(snap_map)

        snap_patterns = {str(p.get("pattern_id")) for p in other.get("patterns", []) if isinstance(p, dict)}
        live_patterns = set(self._patterns)
        identical = (
            not any(added.values())
            and not any(removed.values())
            and not any(changed.values())
            and live_patterns == snap_patterns
        )
        return {
            "identical": identical,
            "added": added,
            "removed": removed,
            "changed": changed,
            "patterns_added": sorted(live_patterns - snap_patterns),
            "patterns_removed": sorted(snap_patterns - live_patterns),
            "counts": {"live": live_totals, "snapshot": snap_totals},
            "metadata_drift": {
                "dedup_threshold": {"live": self._dedup_threshold, "snapshot": other.get("dedup_threshold")},
                "dedup_removed_total": {
                    "live": self._dedup_removed_total,
                    "snapshot": other.get("dedup_removed_total"),
                },
            },
        }

    def stats(self) -> dict[str, Any]:
        """Memory system statistics.

        Returns:
            Dict with memory counts, pattern counts, etc.
        """
        total_short = len(self._short_term)
        total_long = len(self._long_term)
        total_episodic = len(self._episodic)
        total_patterns = len(self._patterns)

        avg_strength_short = sum(m.strength for m in self._short_term) / total_short if total_short else 0
        avg_strength_long = sum(m.strength for m in self._long_term) / total_long if total_long else 0

        # Platform distribution
        platform_dist: dict[str, int] = defaultdict(int)
        for pool in [self._short_term, self._long_term, self._episodic]:
            for m in pool:
                platform_dist[m.platform] += 1

        return {
            "short_term_count": total_short,
            "long_term_count": total_long,
            "episodic_count": total_episodic,
            "pattern_count": total_patterns,
            "avg_strength_short": round(avg_strength_short, 4),
            "avg_strength_long": round(avg_strength_long, 4),
            "platform_distribution": dict(platform_dist),
            "last_consolidation": self._last_consolidation,
            "compression": self.compression_stats(),
            "dedup": self.dedup_stats(),
            "archive": self.archive_stats(),
        }
