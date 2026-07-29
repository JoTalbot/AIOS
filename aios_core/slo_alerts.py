"""SLO alerting on top of the aggregate health score (v11.10.0).

Evaluates the v11.9.0 health score (aggregate AND per-component values)
against two thresholds and emits machine-usable alerts: an operator
(or a systemd unit, or a Prometheus Alertmanager bridge polling
``GET /api/health/alerts``) learns not just THAT the system is degraded,
but WHICH pillar — substrate fleet, scheduler efficiency or memory
vitality — is dragging it down.
"""

from __future__ import annotations

from typing import Any

from .health_score import compute_health_score

__all__ = ["DEFAULT_SLO_CRITICAL", "DEFAULT_SLO_WARNING", "evaluate_health_alerts"]

DEFAULT_SLO_WARNING = 80.0
DEFAULT_SLO_CRITICAL = 50.0

_SEVERITY_ORDER = {"critical": 2, "warning": 1}


def evaluate_health_alerts(
    *,
    memory_system: Any = None,
    engine: Any = None,
    scheduler: Any = None,
    warning: float = DEFAULT_SLO_WARNING,
    critical: float = DEFAULT_SLO_CRITICAL,
) -> dict[str, Any]:
    """Compare the live health score against SLO thresholds.

    Args:
        memory_system/engine/scheduler: live runtime singletons (same
            contract as compute_health_score). All optional.
        warning: scores strictly BELOW this raise a warning alert.
        critical: scores strictly BELOW this raise a critical alert.
            Must be lower than warning.

    Returns:
        {"ok", "alert_count", "worst_severity", "thresholds", "alerts",
        "score", "status"} — ok=True iff no alert fired.
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
    }
