"""
Enhanced Monitoring and Logging System for AIOS External Integration

Provides comprehensive monitoring, alerting, and logging capabilities for external integrations.
Includes real-time metrics, performance monitoring, and automated alerting.
"""

import asyncio
import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from aios_core.logging_config import JSONFormatter, setup_logging
from aios_core.telemetry import MetricCounter, MetricGauge, MetricHistogram
from aios_core.tracing import tracer

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of monitoring alerts."""

    PERFORMANCE = "performance"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"
    SECURITY = "security"
    INTEGRATION_FAILURE = "integration_failure"
    API_RATE_LIMIT = "api_rate_limit"


@dataclass
class Alert:
    """Monitoring alert structure."""

    id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    timestamp: float
    source: str
    metadata: dict[str, Any] | None = None
    resolved: bool = False
    resolved_at: float | None = None


@dataclass
class MetricSnapshot:
    """Snapshot of system metrics."""

    timestamp: float
    cpu_usage: float
    memory_usage: float
    active_connections: int
    request_rate: float
    error_rate: float
    response_time_avg: float
    response_time_p95: float
    response_time_p99: float
    integration_events_processed: int
    integration_events_failed: int


class AlertManager:
    """Manages monitoring alerts and notifications."""

    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_rules: List[Callable] = []
        self.notification_handlers: List[Callable] = []
        self._running = False

    def add_alert_rule(self, rule: Callable) -> None:
        """Add an alert evaluation rule."""
        self.alert_rules.append(rule)
        logger.info(f"Added alert rule: {rule.__name__}")

    def add_notification_handler(self, handler: Callable) -> None:
        """Add a notification handler for alerts."""
        self.notification_handlers.append(handler)
        logger.info(f"Added notification handler: {handler.__name__}")

    async def evaluate_rules(self, metrics: MetricSnapshot) -> None:
        """Evaluate all alert rules against current metrics."""
        for rule in self.alert_rules:
            try:
                alerts = await rule(metrics)
                for alert in alerts:
                    await self.create_alert(alert)
            except Exception as e:
                logger.error(f"Error evaluating alert rule {rule.__name__}: {e}")

    async def create_alert(self, alert: Alert) -> None:
        """Create a new monitoring alert."""
        alert.id = f"alert_{int(time.time())}_{hash(alert.title)}"
        alert.timestamp = time.time()

        self.alerts[alert.id] = alert
        self.alert_history.append(alert)

        logger.warning(f"Alert created: {alert.title} ({alert.severity.value})")

        # Send notifications
        for handler in self.notification_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Error in notification handler {handler.__name__}: {e}")

    async def resolve_alert(self, alert_id: str) -> None:
        """Resolve an alert."""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = time.time()
            logger.info(f"Alert resolved: {alert.title}")

    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        return [alert for alert in self.alerts.values() if not alert.resolved]

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        return list(self.alert_history)[-limit:]


class PerformanceMonitor:
    """Monitors system performance and metrics."""

    def __init__(self):
        self.metrics = {
            "request_count": MetricCounter("requests_total", "Total number of requests"),
            "error_count": MetricCounter("errors_total", "Total number of errors"),
            "response_time": MetricHistogram("response_time_seconds", "Response time distribution"),
            "active_connections": MetricGauge("active_connections", "Number of active connections"),
            "cpu_usage": MetricGauge("cpu_usage_percent", "CPU usage percentage"),
            "memory_usage": MetricGauge("memory_usage_percent", "Memory usage percentage"),
        }

        self.request_times = deque(maxlen=1000)
        self.error_rates = deque(maxlen=100)
        self.performance_baseline = {
            "cpu_threshold": 80.0,
            "memory_threshold": 85.0,
            "error_rate_threshold": 0.05,
            "response_time_threshold": 1.0,
        }

    def record_request(self, response_time: float, status_code: int = 200) -> None:
        """Record a request and its response time."""
        self.metrics["request_count"].add(1)
        self.metrics["response_time"].observe(response_time)
        self.request_times.append((time.time(), response_time, status_code))

        if status_code >= 400:
            self.metrics["error_count"].add(1)
            self.error_rates.append((time.time(), 1))
        else:
            self.error_rates.append((time.time(), 0))

    def update_system_metrics(self, cpu_usage: float, memory_usage: float) -> None:
        """Update system resource metrics."""
        self.metrics["cpu_usage"].set(cpu_usage)
        self.metrics["memory_usage"].set(memory_usage)

    def get_performance_snapshot(self) -> MetricSnapshot:
        """Get current performance metrics snapshot."""
        now = time.time()

        # Calculate request rate (requests per second)
        recent_requests = [t for t, _, _ in self.request_times if now - t < 60]
        request_rate = len(recent_requests) / 60.0

        # Calculate error rate
        recent_errors = [e for t, e in self.error_rates if now - t < 60]
        error_rate = sum(recent_errors) / max(len(recent_errors), 1)

        # Calculate response time statistics
        response_times = [rt for _, rt, _ in self.request_times]
        response_time_avg = sum(response_times) / max(len(response_times), 1)
        response_time_sorted = sorted(response_times)
        response_time_p95 = (
            response_time_sorted[int(len(response_time_sorted) * 0.95)]
            if response_time_sorted
            else 0
        )
        response_time_p99 = (
            response_time_sorted[int(len(response_time_sorted) * 0.99)]
            if response_time_sorted
            else 0
        )

        return MetricSnapshot(
            timestamp=now,
            cpu_usage=self.metrics["cpu_usage"].value,
            memory_usage=self.metrics["memory_usage"].value,
            active_connections=self.metrics["active_connections"].value,
            request_rate=request_rate,
            error_rate=error_rate,
            response_time_avg=response_time_avg,
            response_time_p95=response_time_p95,
            response_time_p99=response_time_p99,
            integration_events_processed=self.metrics["request_count"].value,
            integration_events_failed=self.metrics["error_count"].value,
        )


class IntegrationMonitor:
    """Monitors external integration performance and health."""

    def __init__(self):
        self.integration_metrics = defaultdict(self._create_integration_metrics)

        self.health_checks = {}
        self._running = False

    def _create_integration_metrics(self) -> dict[str, Any]:
        """Factory for per-integration metric objects (name set on first use)."""
        return {
            "requests": MetricCounter("integration_requests", "Requests for integration"),
            "errors": MetricCounter("integration_errors", "Errors for integration"),
            "response_time": MetricHistogram(
                "integration_response_time", "Response time for integration"
            ),
            "last_activity": MetricGauge(
                "integration_last_activity", "Last activity for integration"
            ),
        }

    def register_integration(self, name: str, health_check: Callable) -> None:
        """Register an integration for monitoring."""
        self.health_checks[name] = health_check
        logger.info(f"Registered integration for monitoring: {name}")

    def record_integration_request(
        self, integration: str, response_time: float, success: bool = True
    ):
        """Record an integration request."""
        metrics = self.integration_metrics[integration]
        metrics["requests"].add(1)
        metrics["response_time"].observe(response_time)
        metrics["last_activity"].set(time.time())

        if not success:
            metrics["errors"].add(1)

    async def run_health_checks(self) -> Dict[str, dict[str, Any]]:
        """Run health checks for all registered integrations."""
        results = {}

        for name, health_check in self.health_checks.items():
            try:
                result = await health_check()
                results[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "timestamp": time.time(),
                    "details": result if isinstance(result, dict) else {},
                }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "timestamp": time.time(),
                    "error": str(e),
                }

        return results


class EnhancedLoggingManager:
    """Enhanced logging manager with structured logging and log aggregation."""

    def __init__(self):
        self.loggers = {}
        self.log_aggregators = []
        self._setup_loggers()

    def _setup_loggers(self):
        """Setup structured loggers for different components."""
        # Integration logger
        integration_logger = logging.getLogger("aios_integration")
        integration_logger.setLevel(logging.INFO)

        # Performance logger
        performance_logger = logging.getLogger("aios_performance")
        performance_logger.setLevel(logging.INFO)

        # Alert logger
        alert_logger = logging.getLogger("aios_alerts")
        alert_logger.setLevel(logging.WARNING)

        # Setup formatters
        json_formatter = JSONFormatter()

        # Add handlers
        for logger_name, logger_obj in [
            ("aios_integration", integration_logger),
            ("aios_performance", performance_logger),
            ("aios_alerts", alert_logger),
        ]:
            handler = logging.StreamHandler()
            handler.setFormatter(json_formatter)
            logger_obj.addHandler(handler)
            self.loggers[logger_name] = logger_obj

    def add_log_aggregator(self, aggregator: Callable) -> None:
        """Add a log aggregator for external log collection."""
        self.log_aggregators.append(aggregator)
        logger.info(f"Added log aggregator: {aggregator.__name__}")

    def log_integration_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Log integration events."""
        self.loggers["aios_integration"].info(
            f"Integration event: {event_type}",
            extra={"event_type": event_type, "data": data},
        )

    def log_performance_metrics(self, metrics: MetricSnapshot) -> None:
        """Log performance metrics."""
        self.loggers["aios_performance"].info(
            "Performance metrics snapshot",
            extra={
                "cpu_usage": metrics.cpu_usage,
                "memory_usage": metrics.memory_usage,
                "request_rate": metrics.request_rate,
                "error_rate": metrics.error_rate,
                "response_time_avg": metrics.response_time_avg,
            },
        )

    def log_alert(self, alert: Alert) -> None:
        """Log monitoring alerts."""
        self.loggers["aios_alerts"].warning(
            f"Alert: {alert.title}",
            extra={
                "alert_id": alert.id,
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "source": alert.source,
                "resolved": alert.resolved,
            },
        )


class MonitoringSystem:
    """Main monitoring system that coordinates all monitoring components."""

    def __init__(self):
        self.alert_manager = AlertManager()
        self.performance_monitor = PerformanceMonitor()
        self.integration_monitor = IntegrationMonitor()
        self.logging_manager = EnhancedLoggingManager()
        self._running = False
        self.monitoring_interval = 30  # seconds

        # Setup default alert rules
        self._setup_default_alert_rules()

        # Setup default notification handlers
        self._setup_default_notification_handlers()

    def _setup_default_alert_rules(self):
        """Setup default alert evaluation rules."""

        async def high_cpu_rule(metrics: MetricSnapshot) -> List[Alert]:
            if metrics.cpu_usage > 80:
                return [
                    Alert(
                        alert_type=AlertType.RESOURCE_USAGE,
                        severity=AlertSeverity.HIGH,
                        title="High CPU Usage",
                        message=f"CPU usage is {metrics.cpu_usage:.1f}%",
                        source="performance_monitor",
                        metadata={"cpu_usage": metrics.cpu_usage},
                    )
                ]
            return []

        async def high_error_rate_rule(metrics: MetricSnapshot) -> List[Alert]:
            if metrics.error_rate > 0.05:
                return [
                    Alert(
                        alert_type=AlertType.ERROR_RATE,
                        severity=AlertSeverity.MEDIUM,
                        title="High Error Rate",
                        message=f"Error rate is {metrics.error_rate:.2%}",
                        source="performance_monitor",
                        metadata={"error_rate": metrics.error_rate},
                    )
                ]
            return []

        async def integration_failure_rule(metrics: MetricSnapshot) -> List[Alert]:
            if metrics.integration_events_failed > 10:
                return [
                    Alert(
                        alert_type=AlertType.INTEGRATION_FAILURE,
                        severity=AlertSeverity.CRITICAL,
                        title="Integration Failures",
                        message=f"High number of integration failures: {metrics.integration_events_failed}",
                        source="integration_monitor",
                        metadata={"failed_events": metrics.integration_events_failed},
                    )
                ]
            return []

        self.alert_manager.add_alert_rule(high_cpu_rule)
        self.alert_manager.add_alert_rule(high_error_rate_rule)
        self.alert_manager.add_alert_rule(integration_failure_rule)

    def _setup_default_notification_handlers(self):
        """Setup default notification handlers."""

        async def log_notification(alert: Alert) -> None:
            """Log alerts to the logging system."""
            self.logging_manager.log_alert(alert)

        async def console_notification(alert: Alert) -> None:
            """Log alerts to console via the logging system."""
            logger.critical(
                "ALERT: %s (%s) — %s",
                alert.title,
                alert.severity.value,
                alert.message,
            )

        self.alert_manager.add_notification_handler(log_notification)
        self.alert_manager.add_notification_handler(console_notification)

    async def start_monitoring(self) -> None:
        """Start the monitoring system."""
        self._running = True
        logger.info("Monitoring system started")

        while self._running:
            try:
                # Get performance snapshot
                snapshot = self.performance_monitor.get_performance_snapshot()

                # Log metrics
                self.logging_manager.log_performance_metrics(snapshot)

                # Evaluate alert rules
                await self.alert_manager.evaluate_rules(snapshot)

                # Run integration health checks
                health_results = await self.integration_monitor.run_health_checks()

                # Log health check results
                for integration, result in health_results.items():
                    self.logging_manager.log_integration_event(
                        "health_check", {"integration": integration, "result": result}
                    )

                # Wait for next interval
                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)

    def stop_monitoring(self) -> None:
        """Stop the monitoring system."""
        self._running = False
        logger.info("Monitoring system stopped")

    def get_monitoring_dashboard_data(self) -> dict[str, Any]:
        """Get data for monitoring dashboard."""
        return {
            "active_alerts": len(self.alert_manager.get_active_alerts()),
            "performance_metrics": self.performance_monitor.get_performance_snapshot(),
            "integration_health": self.integration_monitor.health_checks,
            "alert_history": len(self.alert_manager.alert_history),
        }


def create_monitoring_system() -> MonitoringSystem:
    """Create and configure the monitoring system."""
    system = MonitoringSystem()

    # Register some default integrations for monitoring
    async def default_api_health_check() -> None:
        """Default API health check."""
        return {"status": "healthy", "timestamp": time.time()}

    system.integration_monitor.register_integration("api", default_api_health_check)

    return system
