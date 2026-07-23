"""Webhook Prometheus Metrics

Exports webhook-related metrics for Prometheus monitoring:
- aios_webhook_targets_total — total number of registered webhook targets
- aios_webhook_triggers_total — total webhook triggers (by event type)
- aios_webhook_errors_total — total webhook errors (by target)
- aios_webhook_notifications_total — total notifications sent (by event, severity)
- aios_webhook_history_size — current notification history size

Usage:
    from aios_core.webhook_metrics import register_webhook_metrics
    register_webhook_metrics(webhook_manager)
"""

from typing import Optional

from .metrics_exporter import metrics_exporter
from .webhook_manager import WebhookManager


def register_webhook_metrics(manager: Optional[WebhookManager] = None) -> None:
    """Register webhook metrics with the global metrics exporter.

    Call this periodically or after webhook operations to update metrics.
    """
    if manager is None:
        return

    report = manager.health_report()

    # Total targets
    metrics_exporter.set_gauge("aios_webhook_targets_total", report["total_targets"])
    metrics_exporter.set_gauge("aios_webhook_targets_active", report["active_targets"])
    metrics_exporter.set_gauge("aios_webhook_targets_inactive", report["inactive_targets"])

    # Total triggers and errors
    metrics_exporter.set_gauge("aios_webhook_triggers_total", report["total_triggers"])
    metrics_exporter.set_gauge("aios_webhook_errors_total", report["total_errors"])

    # History size
    metrics_exporter.set_gauge("aios_webhook_history_size", report["history_size"])

    # Per-target metrics
    for target in manager.list_targets():
        name = target["name"]
        labels = {"target": name, "url": target["url"]}

        metrics_exporter.set_gauge(
            "aios_webhook_target_triggers",
            target["trigger_count"],
            labels=labels,
        )
        metrics_exporter.set_gauge(
            "aios_webhook_target_errors",
            target["error_count"],
            labels=labels,
        )
        active_val = 1 if target.get("active", True) else 0
        metrics_exporter.set_gauge(
            "aios_webhook_target_active",
            active_val,
            labels=labels,
        )


def get_webhook_prometheus_text(manager: Optional[WebhookManager] = None) -> str:
    """Generate Prometheus-format text for webhook metrics.

    Returns a string suitable for /metrics endpoint.
    """
    register_webhook_metrics(manager)

    lines = [
        "# HELP aios_webhook_targets_total Total number of registered webhook targets",
        "# TYPE aios_webhook_targets_total gauge",
        f"aios_webhook_targets_total {metrics_exporter.gauges.get('aios_webhook_targets_total', 0)}",
        "",
        "# HELP aios_webhook_targets_active Number of active webhook targets",
        "# TYPE aios_webhook_targets_active gauge",
        f"aios_webhook_targets_active {metrics_exporter.gauges.get('aios_webhook_targets_active', 0)}",
        "",
        "# HELP aios_webhook_targets_inactive Number of inactive webhook targets",
        "# TYPE aios_webhook_targets_inactive gauge",
        f"aios_webhook_targets_inactive {metrics_exporter.gauges.get('aios_webhook_targets_inactive', 0)}",
        "",
        "# HELP aios_webhook_triggers_total Total webhook triggers across all targets",
        "# TYPE aios_webhook_triggers_total gauge",
        f"aios_webhook_triggers_total {metrics_exporter.gauges.get('aios_webhook_triggers_total', 0)}",
        "",
        "# HELP aios_webhook_errors_total Total webhook errors across all targets",
        "# TYPE aios_webhook_errors_total gauge",
        f"aios_webhook_errors_total {metrics_exporter.gauges.get('aios_webhook_errors_total', 0)}",
        "",
        "# HELP aios_webhook_history_size Current notification history size",
        "# TYPE aios_webhook_history_size gauge",
        f"aios_webhook_history_size {metrics_exporter.gauges.get('aios_webhook_history_size', 0)}",
    ]

    # Per-target metrics
    if manager:
        for target in manager.list_targets():
            name = target["name"]
            url = target["url"]
            labels = f'target="{name}",url="{url}"'

            lines.append("")
            lines.append(f"# HELP aios_webhook_target_triggers Triggers for target {name}")
            lines.append(f"# TYPE aios_webhook_target_triggers gauge")
            lines.append(f"aios_webhook_target_triggers{{{labels}}} {target['trigger_count']}")

            lines.append(f"# HELP aios_webhook_target_errors Errors for target {name}")
            lines.append(f"# TYPE aios_webhook_target_errors gauge")
            lines.append(f"aios_webhook_target_errors{{{labels}}} {target['error_count']}")

            active_val = 1 if target.get("active", True) else 0
            lines.append(f"# HELP aios_webhook_target_active Whether target {name} is active")
            lines.append(f"# TYPE aios_webhook_target_active gauge")
            lines.append(f"aios_webhook_target_active{{{labels}}} {active_val}")

    return "\n".join(lines)
