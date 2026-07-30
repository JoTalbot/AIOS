"""SLO alerting on top of the aggregate health score (v11.10.0).

Evaluates the v11.9.0 health score (aggregate AND per-component values)
against two thresholds and emits machine-usable alerts: an operator
(or a systemd unit, or a Prometheus Alertmanager bridge polling
``GET /api/health/alerts``) learns not just THAT the system is degraded,
but WHICH pillar — substrate fleet, scheduler efficiency or memory
vitality — is dragging it down.

v11.14.0 adds energy-budget pressure alerting: the rolling budget's
spent/limit ratio is evaluated against warning/critical ratios so an
operator sees budget exhaustion BEFORE dispatches start failing with
``energy_budget_exceeded`` violations.
"""

from __future__ import annotations

from typing import Any

from .health_score import compute_health_score

__all__ = [
    "DEFAULT_BUDGET_CRITICAL_RATIO",
    "DEFAULT_BUDGET_WARNING_RATIO",
    "DEFAULT_SLO_CRITICAL",
    "DEFAULT_SLO_WARNING",
    "evaluate_budget_alerts",
    "evaluate_health_alerts",
]

DEFAULT_SLO_WARNING = 80.0
DEFAULT_SLO_CRITICAL = 50.0

#: Default spent/limit ratios for budget pressure alerts (v11.14.0).
DEFAULT_BUDGET_WARNING_RATIO = 0.8
DEFAULT_BUDGET_CRITICAL_RATIO = 1.0

_SEVERITY_ORDER = {"critical": 2, "warning": 1}


def evaluate_health_alerts(
    *,
    memory_system: Any = None,
    engine: Any = None,
    scheduler: Any = None,
    warning: float = DEFAULT_SLO_WARNING,
    critical: float = DEFAULT_SLO_CRITICAL,
    budget_warning_ratio: float = DEFAULT_BUDGET_WARNING_RATIO,
    budget_critical_ratio: float = DEFAULT_BUDGET_CRITICAL_RATIO,
) -> dict[str, Any]:
    """Compare the live health score against SLO thresholds.

    Args:
        memory_system/engine/scheduler: live runtime singletons (same
            contract as compute_health_score). All optional.
        warning: scores strictly BELOW this raise a warning alert.
        critical: scores strictly BELOW this raise a critical alert.
            Must be lower than warning.
        budget_warning_ratio/budget_critical_ratio: rolling-budget
            pressure ratios alerting alongside the health pillars
            (v11.15.0). Budget alerts carry subject "energy_budget";
            the "budget" sub-report is included in the return dict.

    Returns:
        {"ok", "alert_count", "worst_severity", "thresholds", "alerts",
        "score", "status", "budget"} — ok=True iff no alert fired
        (budget alerts included since v11.15.0).
    """
    warning = float(warning)
    critical = float(critical)
    if not 0.0 <= critical < warning <= 100.0:
        raise ValueError("thresholds must satisfy 0 <= critical < warning <= 100")

    health = compute_health_score(memory_system=memory_system, engine=engine, scheduler=scheduler)
    score = health["score"]

    alerts: list[dict[str, Any]] = []

    def evaluate(subject: str, value: float | None) -> None:
        if value is None:
            return
        if value < critical:
            severity = "critical"
        elif value < warning:
            severity = "warning"
        else:
            return
        alerts.append(
            {
                "subject": subject,
                "severity": severity,
                "score": value,
                "message": f"{subject} at {value} is below the {severity} threshold "
                f"({critical if severity == 'critical' else warning})",
            }
        )

    evaluate("aggregate", score)
    for name, component in health["components"].items():
        if component["available"]:
            evaluate(name, component["score"])

    # Budget pressure rolls up into the unified report (v11.15.0).
    budget_report = evaluate_budget_alerts(
        scheduler=scheduler,
        warning_ratio=budget_warning_ratio,
        critical_ratio=budget_critical_ratio,
    )
    alerts.extend(budget_report["alerts"])

    worst = None
    if alerts:
        worst = max(alerts, key=lambda a: _SEVERITY_ORDER[a["severity"]])["severity"]

    return {
        "ok": not alerts,
        "alert_count": len(alerts),
        "worst_severity": worst,
        "thresholds": {"warning": warning, "critical": critical},
        "alerts": alerts,
        "score": score,
        "status": health["status"],
        "evaluated": health["evaluated"],
        "budget": budget_report,
    }


def evaluate_budget_alerts(
    *,
    scheduler: Any = None,
    warning_ratio: float = DEFAULT_BUDGET_WARNING_RATIO,
    critical_ratio: float = DEFAULT_BUDGET_CRITICAL_RATIO,
) -> dict[str, Any]:
    """Evaluate rolling energy-budget pressure against ratios (v11.14.0).

    Pressure = spent/limit for the current window. Unlike the health
    scores, HIGHER is worse: pressure >= critical_ratio fires a critical
    alert (dispatches may already be failing with budget-exceeded
    violations), pressure >= warning_ratio fires a warning. Pressure can
    exceed 1.0 after a runtime reconfigure lowered the limit below the
    current window's spend.

    Args:
        scheduler: live ``EnergyAwareScheduler`` (budget may be absent).
        warning_ratio: pressure at/above this raises a warning.
        critical_ratio: pressure at/above this raises a critical alert;
            must exceed warning_ratio.

    Returns:
        {"available", "ok", "status", "pressure", "alert_count",
        "worst_severity", "thresholds", "alerts", "budget"} —
        available=False (status "no_budget") when the scheduler has no
        rolling budget configured.
    """
    try:
        warning_ratio = float(warning_ratio)
        critical_ratio = float(critical_ratio)
    except (TypeError, ValueError):
        raise ValueError("warning_ratio and critical_ratio must be numbers") from None
    if not 0.0 <= warning_ratio < critical_ratio:
        raise ValueError("ratios must satisfy 0 <= warning_ratio < critical_ratio")

    budget = getattr(scheduler, "energy_budget", None) if scheduler is not None else None
    if budget is None:
        return {
            "available": False,
            "ok": True,
            "status": "no_budget",
            "pressure": None,
            "alert_count": 0,
            "worst_severity": None,
            "thresholds": {"warning_ratio": warning_ratio, "critical_ratio": critical_ratio},
            "alerts": [],
            "budget": None,
        }

    pressure = budget.pressure()
    state = budget.to_dict()
    alerts: list[dict[str, Any]] = []
    if pressure >= critical_ratio:
        severity = "critical"
    elif pressure >= warning_ratio:
        severity = "warning"
    else:
        severity = None
    if severity:
        alerts.append(
            {
                "subject": "energy_budget",
                "severity": severity,
                "pressure": round(pressure, 4),
                "spent": state["spent"],
                "limit": state["limit"],
                "message": f"energy budget pressure {pressure:.2f} (spent {state['spent']}/{state['limit']} "
                f"per {state['window_seconds']}s) reached the {severity} ratio "
                f"({critical_ratio if severity == 'critical' else warning_ratio})",
            }
        )

    return {
        "available": True,
        "ok": not alerts,
        "status": severity or "ok",
        "pressure": round(pressure, 4),
        "alert_count": len(alerts),
        "worst_severity": severity,
        "thresholds": {"warning_ratio": warning_ratio, "critical_ratio": critical_ratio},
        "alerts": alerts,
        "budget": state,
    }
