"""AIOS Learning Engine v3.0.0

Processes system experience and learning signals. Persists experiences
using MemoryManager with category="operational" and tags=["learning"].
Supports pattern extraction, recommendations, and task completion recording.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Optional

__all__ = ["LearningEngine"]

if TYPE_CHECKING:
    from .memory_manager import MemoryManager
    from .storage import Database


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
        self._prediction_count = 0
        self._last_correlations: list[dict] = []

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
        success = (
            task.status.value == "completed"
            if hasattr(task.status, "value")
            else str(task.status) == "completed"
        )
        step_results = []
        if hasattr(task, "steps"):
            for s in task.steps:
                step_info = {
                    "name": s.name if hasattr(s, "name") else str(s),
                    "status": (s.status.value if hasattr(s.status, "value") else str(s.status)),
                }
                if hasattr(s, "error") and s.error:
                    step_info["error"] = s.error
                step_results.append(step_info)

        experience = {
            "task_name": task.name if hasattr(task, "name") else str(task),
            "task_id": task.id if hasattr(task, "id") else "unknown",
            "success": success,
            "total_steps": len(task.steps) if hasattr(task, "steps") else 0,
            "step_results": step_results,
            "risk_level": task.risk_level if hasattr(task, "risk_level") else "unknown",
        }

        return self.record(
            experience=experience,
            tags=["task_completion", "success" if success else "failure"],
        )

    def extract_patterns(self, limit: int = 50) -> list[dict]:
        """Find patterns in learning experiences, enriched with per-task statistics.

        Searches for learning experiences, filters for successful ones,
        and augments each pattern with per-task success rates and counts.

        Returns:
            List of pattern dicts with action, outcome, confidence,
            memory_id, success_rate, total_attempts, and success_count.
        """
        if self.memory is None:
            return []

        memories = self.memory.search(
            tag="learning",
            category="operational",
            limit=limit,
        )

        # --- first pass: compute per-task statistics ---
        task_stats: dict[str, dict[str, int]] = {}
        for mem in memories:
            content = mem.get("content", {})
            exp = content.get("experience", {})
            task_name = exp.get("task_name")
            if not task_name:
                continue
            entry = task_stats.setdefault(task_name, {"success": 0, "total": 0})
            entry["total"] += 1
            if exp.get("success", False):
                entry["success"] += 1

        # --- second pass: build enriched patterns for successes ---
        patterns = []
        for mem in memories:
            content = mem.get("content", {})
            exp = content.get("experience", {})
            success = exp.get("success", False)
            if success:
                task_name = exp.get("task_name")
                stats = task_stats.get(task_name, {"success": 0, "total": 0})
                total = stats["total"]
                succ = stats["success"]
                patterns.append(
                    {
                        "action": task_name,
                        "outcome": "success",
                        "confidence": mem.get("confidence", exp.get("confidence", 0.5)),
                        "memory_id": mem.get("id"),
                        "success_rate": round(succ / total, 4) if total else 0.0,
                        "total_attempts": total,
                        "success_count": succ,
                    }
                )

        return patterns

    def analyze_temporal_patterns(self, hours: int = 168) -> list[dict]:
        """Analyse success/failure rates by hour-of-day over recent history.

        Args:
            hours: How many hours back to look (default 168 = 1 week).

        Returns:
            List of dicts keyed by task_name with best/worst hours and
            per-hour success rates.
        """
        if self.memory is None:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_iso = cutoff.isoformat()

        memories = self.memory.search(
            tag="learning",
            category="operational",
            limit=10000,
        )

        # Filter to the time window
        recent = []
        for mem in memories:
            created = mem.get("created_at")
            if created and created >= cutoff_iso:
                recent.append(mem)

        if not recent:
            return []

        # Group by (task_name, hour)
        # task_hour[task][(hour)] = {"success": n, "total": m}
        task_hour: dict[str, dict[int, dict[str, int]]] = {}
        for mem in recent:
            content = mem.get("content", {})
            exp = content.get("experience", {})
            task_name = exp.get("task_name")
            if not task_name:
                continue
            created = mem.get("created_at", "")
            try:
                dt = datetime.fromisoformat(created)
                hour = dt.hour
            except (ValueError, TypeError):
                continue
            hours_map = task_hour.setdefault(task_name, {})
            bucket = hours_map.setdefault(hour, {"success": 0, "total": 0})
            bucket["total"] += 1
            if exp.get("success", False):
                bucket["success"] += 1

        results = []
        for task_name, hour_map in task_hour.items():
            hourly_success_rates: dict[int, float] = {}
            best_hour = -1
            worst_hour = -1
            best_rate = -1.0
            worst_rate = 2.0
            total = 0
            for h, counts in hour_map.items():
                rate = round(counts["success"] / counts["total"], 4) if counts["total"] else 0.0
                hourly_success_rates[h] = rate
                total += counts["total"]
                if rate > best_rate:
                    best_rate = rate
                    best_hour = h
                if rate < worst_rate:
                    worst_rate = rate
                    worst_hour = h
            results.append(
                {
                    "task_name": task_name,
                    "best_hour": best_hour,
                    "worst_hour": worst_hour,
                    "hourly_success_rates": hourly_success_rates,
                    "total": total,
                }
            )

        return results

    def detect_correlations(self, limit: int = 100) -> list[dict]:
        """Detect parameter-value correlations with success.

        For each unique (task_name, param_key, param_value) combination,
        compute the success rate across all matching experiences.

        Args:
            limit: Max number of experiences to scan.

        Returns:
            List of correlation dicts sorted by sample_size desc.
        """
        if self.memory is None:
            self._last_correlations = []
            return []

        memories = self.memory.search(
            tag="learning",
            category="operational",
            limit=limit,
        )

        # key: (task_name, param_key, param_value) -> {"success": n, "total": m}
        buckets: dict[tuple[str, str, str], dict[str, int]] = {}
        for mem in memories:
            content = mem.get("content", {})
            exp = content.get("experience", {})
            task_name = exp.get("task_name")
            if not task_name:
                continue
            success = exp.get("success", False)
            # Inspect flat params in the experience dict
            params = exp.get("params") or {}
            if not isinstance(params, dict):
                params = {}
            for pkey, pval in params.items():
                pval_str = str(pval)
                key = (task_name, pkey, pval_str)
                bucket = buckets.setdefault(key, {"success": 0, "total": 0})
                bucket["total"] += 1
                if success:
                    bucket["success"] += 1

        results = []
        for (task_name, param_key, param_val), counts in buckets.items():
            total = counts["total"]
            rate = round(counts["success"] / total, 4) if total else 0.0
            results.append(
                {
                    "task_name": task_name,
                    "parameter": param_key,
                    "value": param_val,
                    "success_rate": rate,
                    "sample_size": total,
                }
            )

        # Sort by sample_size descending so the most reliable come first
        results.sort(key=lambda r: r["sample_size"], reverse=True)
        self._last_correlations = results
        return results

    def predict_success(self, task_name: str, params: dict = None) -> dict:
        """Predict the likelihood of success for a given task.

        Uses historical success rate, temporal patterns, and parameter
        correlations to produce an estimate.

        Args:
            task_name: Name of the task to predict for.
            params: Optional parameter dict to factor in.

        Returns:
            Prediction dict with predicted_success_rate, confidence,
            contributing factors, and a recommendation.
        """
        self._prediction_count += 1

        if self.memory is None:
            return {
                "task_name": task_name,
                "predicted_success_rate": 0.0,
                "confidence": 0.0,
                "factors": [{"factor": "no_storage", "impact": "unknown", "value": 0.0}],
                "recommendation": "No learning data available; cannot predict.",
            }

        factors: list[dict[str, str | float]] = []

        # --- Factor 1: Historical success rate ---
        all_mem = self.memory.search(
            tag="learning",
            category="operational",
            limit=10000,
        )
        task_hist_success = 0
        task_hist_total = 0
        for mem in all_mem:
            exp = mem.get("content", {}).get("experience", {})
            if exp.get("task_name") == task_name:
                task_hist_total += 1
                if exp.get("success", False):
                    task_hist_success += 1
        hist_rate = round(task_hist_success / task_hist_total, 4) if task_hist_total else 0.0
        if task_hist_total > 0:
            factors.append(
                {
                    "factor": "historical_success_rate",
                    "impact": "base_rate",
                    "value": hist_rate,
                }
            )

        # --- Factor 2: Time-of-day ---
        current_hour = datetime.now(timezone.utc).hour
        temporal_data = self.analyze_temporal_patterns()
        temporal_rate: Optional[float] = None
        for td in temporal_data:
            if td["task_name"] == task_name and current_hour in td["hourly_success_rates"]:
                temporal_rate = td["hourly_success_rates"][current_hour]
                impact = "positive" if temporal_rate >= hist_rate else "negative"
                factors.append({"factor": "time_of_day", "impact": impact, "value": temporal_rate})
                break

        # --- Factor 3: Parameter correlations ---
        if params and self._last_correlations:
            for corr in self._last_correlations:
                if corr["task_name"] == task_name and corr["parameter"] in params:
                    if str(params[corr["parameter"]]) == corr["value"]:
                        impact = "positive" if corr["success_rate"] >= 0.5 else "negative"
                        factors.append(
                            {
                                "factor": f"param_{corr['parameter']}={corr['value']}",
                                "impact": impact,
                                "value": corr["success_rate"],
                            }
                        )

        # --- Combine into a single prediction ---
        if not factors:
            return {
                "task_name": task_name,
                "predicted_success_rate": 0.0,
                "confidence": 0.0,
                "factors": [],
                "recommendation": f"No prior data for task '{task_name}'.",
            }

        # Weighted average: historical (0.5), temporal (0.3), param (0.2 per param, capped)
        w_hist = 0.5
        w_temp = 0.3
        w_param = 0.2

        score = 0.0
        weight_sum = 0.0

        for f in factors:
            if f["factor"] == "historical_success_rate":
                score += f["value"] * w_hist
                weight_sum += w_hist
            elif f["factor"] == "time_of_day":
                score += f["value"] * w_temp
                weight_sum += w_temp
            else:
                score += f["value"] * w_param
                weight_sum += w_param

        predicted = round(score / weight_sum, 4) if weight_sum else 0.0
        # Confidence is a function of sample size
        confidence = min(round(task_hist_total / 20.0, 4), 1.0) if task_hist_total else 0.0

        # Recommendation
        if predicted >= 0.8:
            rec = f"High predicted success ({predicted:.0%}). Proceed with task '{task_name}'."
        elif predicted >= 0.5:
            rec = f"Moderate predicted success ({predicted:.0%}). Consider optimisations before running '{task_name}'."
        else:
            rec = f"Low predicted success ({predicted:.0%}). Avoid '{task_name}' or investigate root causes first."

        # Convert factor values to float for JSON serialisation
        serialised_factors = [
            {
                "factor": f["factor"],
                "impact": str(f["impact"]),
                "value": float(f["value"]),
            }
            for f in factors
        ]

        return {
            "task_name": task_name,
            "predicted_success_rate": predicted,
            "confidence": confidence,
            "factors": serialised_factors,
            "recommendation": rec,
        }

    def generate_evolution_suggestions(self) -> list[dict]:
        """Suggest improvements based on learned patterns.

        Identifies tasks with low success rates (suggest improvements) and
        tasks with high variance across hours (suggest stabilisation).

        Returns:
            List of suggestion dicts sorted by priority.
        """
        if self.memory is None:
            return []

        memories = self.memory.search(
            tag="learning",
            category="operational",
            limit=10000,
        )

        # Per-task aggregation
        task_data: dict[str, dict[str, int]] = {}
        for mem in memories:
            exp = mem.get("content", {}).get("experience", {})
            tn = exp.get("task_name")
            if not tn:
                continue
            entry = task_data.setdefault(tn, {"success": 0, "total": 0})
            entry["total"] += 1
            if exp.get("success", False):
                entry["success"] += 1

        # Temporal variance
        temporal = self.analyze_temporal_patterns()
        temporal_variance: dict[str, float] = {}
        for td in temporal:
            rates = list(td["hourly_success_rates"].values())
            if len(rates) >= 2:
                mean = sum(rates) / len(rates)
                var = sum((r - mean) ** 2 for r in rates) / len(rates)
                temporal_variance[td["task_name"]] = var

        suggestions: list[dict] = []

        for task_name, counts in task_data.items():
            total = counts["total"]
            succ = counts["success"]
            rate = round(succ / total, 4) if total else 0.0

            # Low success rate → improvement suggestion
            if rate < 0.5 and total >= 3:
                suggestions.append(
                    {
                        "component": task_name,
                        "suggestion": f"Success rate is {rate:.0%} ({succ}/{total}). Investigate failure causes and refactor.",
                        "priority": "high",
                        "based_on": "low_success_rate",
                        "success_rate": rate,
                    }
                )

            # High temporal variance → stabilisation suggestion
            var = temporal_variance.get(task_name)
            if var is not None and var > 0.04 and total >= 5:  # variance > 0.04 (std > 0.2)
                suggestions.append(
                    {
                        "component": task_name,
                        "suggestion": f"Success rate varies significantly by time of day (variance={var:.4f}). Consider time-independent improvements.",
                        "priority": "medium",
                        "based_on": "high_temporal_variance",
                        "success_rate": rate,
                    }
                )

            # Near-perfect but few samples → suggest more data collection
            if 0.8 <= rate <= 1.0 and total < 5:
                suggestions.append(
                    {
                        "component": task_name,
                        "suggestion": f"Success rate is {rate:.0%} but only {total} attempt(s). Collect more data to confirm reliability.",
                        "priority": "low",
                        "based_on": "insufficient_data",
                        "success_rate": rate,
                    }
                )

        # Sort: high priority first
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda s: priority_order.get(s["priority"], 3))
        return suggestions

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
            results.append(
                {
                    "id": mem.get("id"),
                    "experience": content.get("experience", {}),
                    "confidence": mem.get("confidence", 0.0),
                    "created_at": mem.get("created_at"),
                    "tags": mem.get("tags", []),
                }
            )

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
            1
            for m in learning_items
            if m.get("content", {}).get("experience", {}).get("success", False)
        )

        return {
            "version": "3.0.0",
            "total_experiences": len(learning_items),
            "successful_patterns": successful,
            "storage": "sqlite" if self.db else "memory",
            "temporal_patterns_analyzed": bool(self.analyze_temporal_patterns()),
            "correlations_detected": len(self._last_correlations),
            "predictions_made": self._prediction_count,
        }
