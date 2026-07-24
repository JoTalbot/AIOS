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
                    "avg_latency": sum(e.context.get("latency_ms", 0) for e in entries)
                    / len(entries),
                    "avg_items": sum(e.context.get("items", 0) for e in entries)
                    / len(entries),
                },
                priority=MemoryPriority.HIGH
                if success_rate > 0.7
                else MemoryPriority.NORMAL,
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
                key=lambda e: (
                    e.context.get("items", 0) / max(1, e.context.get("latency_ms", 1))
                ),
            )

            pattern = SuccessPattern(
                pattern_id=f"pattern_{len(self._patterns)}",
                platform=platform,
                action=action,
                success_rate=len(successes)
                / max(
                    1,
                    len(
                        [
                            e
                            for e in self._episodic
                            if e.platform == platform and e.action == action
                        ]
                    ),
                ),
                avg_latency_ms=sum(e.context.get("latency_ms", 0) for e in successes)
                / len(successes),
                avg_items=sum(e.context.get("items", 0) for e in successes)
                / len(successes),
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
        long_term = self.recall(
            platform=platform, action=action, memory_type=MemoryType.LONG_TERM, limit=5
        )

        # Find relevant patterns
        pattern = None
        for p in self._patterns.values():
            if p.platform == platform and p.action == action:
                pattern = p
                break

        # Check for past failures/blocks
        failures = self.recall(
            platform=platform, action=action, result="failure", limit=5
        )

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
                advice["warnings"].append(
                    f"{f.action} failed on {f.platform}: {f.context.get('errors', ['unknown'])}"
                )

        # Add block/ban warnings
        for b in blocks[:3]:
            advice["warnings"].append(
                f"⚠️ BLOCK detected on {b.platform}: avoid {b.context.get('params', {})}"
            )

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
        removed = 0

        self._short_term = [m for m in self._short_term if m.strength >= min_strength]
        self._episodic = [m for m in self._episodic if m.strength >= min_strength]

        # Count removed (approximate)
        removed += len(self._short_term) + len(self._episodic)

        return removed

    def clear_short_term(self) -> int:
        """Clear all short-term memories.

        Returns:
            Number of memories cleared.
        """
        count = len(self._short_term)
        self._short_term.clear()
        return count

    def stats(self) -> dict[str, Any]:
        """Memory system statistics.

        Returns:
            Dict with memory counts, pattern counts, etc.
        """
        total_short = len(self._short_term)
        total_long = len(self._long_term)
        total_episodic = len(self._episodic)
        total_patterns = len(self._patterns)

        avg_strength_short = (
            sum(m.strength for m in self._short_term) / total_short
            if total_short
            else 0
        )
        avg_strength_long = (
            sum(m.strength for m in self._long_term) / total_long if total_long else 0
        )

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
        }
