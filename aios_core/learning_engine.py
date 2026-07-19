"""AIOS Learning Engine v3.0.0

Processes system experience and learning signals. Persists experiences
using MemoryManager with category="operational" and tags=["learning"].
Supports pattern extraction, recommendations, and task completion recording.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .storage import Database
    from .memory_manager import MemoryManager


class LearningEngine:
    """Processes and stores system learning experiences.

    v3.0.0: Full implementation with SQLite persistence via MemoryManager,
    pattern extraction, recommendations, and task completion integration.
    """

    def __init__(self, db: Optional[Database] = None, memory=None):
        self.db = db
        if memory is not None:
            self.memory = memory
        elif db is not None:
            from .memory_manager import MemoryManager
            self.memory = MemoryManager(db=db)
        else:
            self.memory = None

    def record(
        self,
        experience: dict,
        tags: Optional[list[str]] = None,
    ) -> dict:
        """Record a learning experience.

        Args:
            experience: The experience data to record.
            tags: Optional tags for categorization.

        Returns:
            The stored memory item dict.
        """
        if self.memory is None:
            # Fallback: in-memory (no db)
            return {
                "id": "no-db",
                "experience": experience,
                "tags": tags,
                "stored": False,
            }

        all_tags = ["learning"]
        if tags:
            all_tags.extend(tags)

        result = self.memory.store(
            content={
                "type": "learning_experience",
                "experience": experience,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            },
            category="operational",
            tags=all_tags,
            source="learning_engine",
            confidence=experience.get("confidence", 0.8),
        )
        return result

    def learn(self, experience: dict) -> dict:
        """Backward-compatible alias for record()."""
        return self.record(experience)

    def record_task_completion(self, task) -> dict:
        """Extract learnings from a completed Task (orchestrator Task dataclass).

        Args:
            task: A Task object with name, status, steps, etc.

        Returns:
            The stored learning record.
        """
        success = task.status.value == "completed" if hasattr(task.status, 'value') else str(task.status) == "completed"
        step_results = []
        if hasattr(task, 'steps'):
            for s in task.steps:
                step_info = {
                    "name": s.name if hasattr(s, 'name') else str(s),
                    "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
                }
                if hasattr(s, 'error') and s.error:
                    step_info["error"] = s.error
                step_results.append(step_info)

        experience = {
            "task_name": task.name if hasattr(task, 'name') else str(task),
            "task_id": task.id if hasattr(task, 'id') else "unknown",
            "success": success,
            "total_steps": len(task.steps) if hasattr(task, 'steps') else 0,
            "step_results": step_results,
            "risk_level": task.risk_level if hasattr(task, 'risk_level') else "unknown",
        }

        return self.record(
            experience=experience,
            tags=["task_completion", "success" if success else "failure"],
        )

    def extract_patterns(self, limit: int = 50) -> list[dict]:
        """Find patterns in successful experiences.

        Searches for learning experiences and extracts patterns
        from successful ones.

        Returns:
            List of pattern dicts with action, outcome, confidence.
        """
        if self.memory is None:
            return []

        memories = self.memory.search(
            tag="learning",
            category="operational",
            limit=limit,
        )

        patterns = []
        for mem in memories:
            content = mem.get("content", {})
            exp = content.get("experience", {})
            success = exp.get("success", False)
            if success:
                patterns.append({
                    "action": exp.get("task_name"),
                    "outcome": "success",
                    "confidence": mem.get("confidence", exp.get("confidence", 0.5)),
                    "memory_id": mem.get("id"),
                })

        return patterns

    def get_recommendations(self, context: Optional[dict] = None) -> list[dict]:
        """Suggest actions based on past learning.

        Looks at successful patterns and generates recommendations
        relevant to the given context.

        Args:
            context: Optional context dict for filtering.

        Returns:
            List of recommendation dicts.
        """
        patterns = self.extract_patterns()
        if not patterns:
            return []

        recommendations = []
        for pattern in patterns:
            rec = {
                "action": pattern["action"],
                "based_on": pattern["memory_id"],
                "confidence": pattern["confidence"],
                "reason": f"Previously succeeded with confidence {pattern['confidence']:.2f}",
            }
            if context and context.get("task_name"):
                if context["task_name"] == pattern["action"]:
                    rec["relevance"] = "exact_match"
                else:
                    rec["relevance"] = "similar"
            recommendations.append(rec)

        return recommendations

    def history(self, limit: int = 100) -> list[dict]:
        """Retrieve learning history from memory.

        Returns:
            List of learning experience records.
        """
        if self.memory is None:
            return []

        memories = self.memory.search(
            tag="learning",
            category="operational",
            limit=limit,
        )

        results = []
        for mem in memories:
            content = mem.get("content", {})
            results.append({
                "id": mem.get("id"),
                "experience": content.get("experience", {}),
                "confidence": mem.get("confidence", 0.0),
                "created_at": mem.get("created_at"),
                "tags": mem.get("tags", []),
            })

        return results

    def stats(self) -> dict:
        """Return learning engine statistics."""
        if self.memory is None:
            return {
                "version": "3.0.0",
                "total_experiences": 0,
                "successful_patterns": 0,
                "storage": "none",
            }

        learning_items = self.memory.search(
            tag="learning",
            category="operational",
            limit=10000,
        )
        successful = sum(
            1 for m in learning_items
            if m.get("content", {}).get("experience", {}).get("success", False)
        )

        return {
            "version": "3.0.0",
            "total_experiences": len(learning_items),
            "successful_patterns": successful,
            "storage": "sqlite" if self.db else "memory",
        }