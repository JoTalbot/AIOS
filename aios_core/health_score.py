"""Aggregate system health score (v11.9.0).

Combines the three runtime pillars behind the web dashboard — substrate
fleet vitality, energy-scheduler efficiency and agent-memory strength —
into a single 0..100 score with a machine-usable component breakdown.

Components contribute with fixed weights; unavailable ones (e.g. a
scheduler with no dispatches yet carries no efficiency signal) are
dropped and the remaining weights are renormalized, so a cold system
still reports a meaningful score instead of a misleading zero.
"""

from __future__ import annotations

from typing import Any

__all__ = ["compute_health_score"]

_WEIGHT_SUBSTRATE = 0.4
_WEIGHT_SCHEDULER = 0.3
_WEIGHT_MEMORY = 0.3

_HEALTHY = 80.0
_DEGRADED = 50.0


def _clamp(value: float) -> float:
    """Clamp a component score into the 0..100 band."""
    return max(0.0, min(100.0, value))


def _substrate_component(engine: Any) -> dict[str, Any]:
    substrates = [s for s in engine.substrates.values() if s["active"]]
    score = 100.0 * sum(s["health"] for s in substrates) / len(substrates) if substrates else 0.0
    return {
        "available": True,
        "weight": _WEIGHT_SUBSTRATE,
        "score": round(_clamp(score), 2),
        "detail": {
            "active_substrates": len(substrates),
            "min_health": round(min((s["health"] for s in substrates), default=0.0), 4),
        },
    }


def _scheduler_component(scheduler: Any) -> dict[str, Any]:
    report = scheduler.report()
    dispatches = report["dispatches"]
    if dispatches == 0:
        # No signal yet: drop the component instead of punishing a cold system.
        return {"available": False, "weight": _WEIGHT_SCHEDULER, "score": None, "detail": {"dispatches": 0}}
    fallback_rate = report["fallback_dispatches"] / dispatches
    efficiency = 0.6 * min(report["savings_pct"], 100.0) + 0.4 * 100.0 * (1.0 - fallback_rate)
    return {
        "available": True,
        "weight": _WEIGHT_SCHEDULER,
        "score": round(_clamp(efficiency), 2),
        "detail": {
            "dispatches": dispatches,
            "savings_pct": report["savings_pct"],
            "fallback_rate": round(fallback_rate, 4),
        },
    }


def _memory_component(memory_system: Any) -> dict[str, Any]:
    stats = memory_system.stats()
    short, long = stats["short_term_count"], stats["long_term_count"]
    total = short + long
    if total == 0:
        return {"available": False, "weight": _WEIGHT_MEMORY, "score": None, "detail": {"entries": 0}}
    strength = (stats["avg_strength_short"] * short + stats["avg_strength_long"] * long) / total
    return {
        "available": True,
        "weight": _WEIGHT_MEMORY,
        "score": round(_clamp(100.0 * strength), 2),
        "detail": {"entries_scored": total, "avg_strength": round(strength, 4)},
    }


def compute_health_score(
    *,
    memory_system: Any = None,
    engine: Any = None,
    scheduler: Any = None,
) -> dict[str, Any]:
    """Aggregate a 0..100 health score from the live runtime singletons.

    Args:
        memory_system: ``AgentMemorySystem`` instance (memory vitality).
        engine: ``SubstrateConvergenceEngine`` instance (fleet vitality).
        scheduler: ``EnergyAwareScheduler`` instance (routing efficiency).

    Returns:
        {"score", "status", "components", "evaluated"} — status is
        "healthy" (>=80), "degraded" (>=50), "critical" (<50) or
        "no_data" when no component was available at all.
    """
    components: dict[str, dict[str, Any]] = {}
    if engine is not None:
        components["substrate_fleet"] = _substrate_component(engine)
    if scheduler is not None:
        components["scheduler_efficiency"] = _scheduler_component(scheduler)
    if memory_system is not None:
        components["memory_vitality"] = _memory_component(memory_system)

    available = [(name, comp) for name, comp in components.items() if comp["available"]]
    if not available:
        return {"score": None, "status": "no_data", "components": components, "evaluated": 0}

    total_weight = sum(comp["weight"] for _name, comp in available)
    score = sum(comp["score"] * comp["weight"] for _name, comp in available) / total_weight
    if score >= _HEALTHY:
        status = "healthy"
    elif score >= _DEGRADED:
        status = "degraded"
    else:
        status = "critical"
    return {
        "score": round(score, 2),
        "status": status,
        "components": components,
        "evaluated": len(available),
    }
