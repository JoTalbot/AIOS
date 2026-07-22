"""Enhanced Monitoring and Observability System for AIOS.

Provides advanced monitoring capabilities including:
- Real-time dashboards
- Alerting system
- Performance analytics
- Integration with external monitoring tools
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Callable, Union
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from .telemetry import MetricCounter, MetricGauge, MetricHistogram
from .logging_config import setup_logging
from .tracing import tracer


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    metric: str
    condition: str  # e.g., "value > 100", "value < 10"
    threshold: float
    duration: int  # seconds
    severity: str  # "info", "warning", "critical"
    notification_channels: List[str]


@dataclass
class DashboardConfig:
    """Dashboard configuration."""
    name: str
    title: str
    refresh_interval: int  # seconds
    panels: List[Dict[str, Any]]


class MonitoringMetrics:
    """Enhanced metrics for monitoring system."""
    
    def __init__(self):
        self.alerts_triggered = MetricCounter("alerts_triggered", "Total alerts triggered")
        self.alerts_resolved = MetricCounter("alerts_resolved", "Total alerts resolved")
        self.dashboard_requests = MetricCounter("dashboard_requests", "Total dashboard requests")
        self.api_response_time = MetricHistogram("api_response_time", "API response time in ms")
        self.system_health = MetricGauge("system_health", "System health score (0-100)")
        
    def record_alert_triggered(self):
        """Record alert triggered."""
        self.alerts_triggered.add(1)
        
    def record_alert_resolved(self):
        """Record alert resolved."""
        self.alerts_resolved.add(1)
        
    def record_dashboard_request(self):
        """Record dashboard request."""
        self.dashboard_requests.add(1)
        
    def record_response_time(self, duration_ms: float):
        """Record API response time."""
        self.api_response_time.observe(duration_ms)
        
    def set_system_health(self, health_score: float):
        """Set system health score."""
        self.system_health.set(max(0, min(100, health_score)))


class AlertManager:
    """Manages alerting system."""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        self.metrics = MonitoringMetrics()
        self.logger = logging.getLogger("aios.alerts")
        
    def add_rule(self, rule: AlertRule):
        """Add alert rule."""
        self.rules[rule.name] = rule
        self.logger.info(f"Added alert rule: {rule.name}")
        
    def check_metric(self, metric_name: str, value: float, timestamp: float):
        """Check metric against alert rules."""
        for rule_name, rule in self.rules.items():
            if rule.metric == metric_name:
                if self._evaluate_condition(rule.condition, value, rule.threshold):
                    self._trigger_alert(rule, value, timestamp)
                    
    def _evaluate_condition(self, condition: str, value: float, threshold: float) -> bool:
        """Evaluate alert condition."""
        try:
            # Simple condition evaluation (in production, use proper expression parser)
            if condition == "value > threshold":
                return value > threshold
            elif condition == "value < threshold":
                return value < threshold
            elif condition == "value >= threshold":
                return value >= threshold
            elif condition == "value <= threshold":
                return value <= threshold
            return False
        except Exception as e:
            self.logger.error(f"Error evaluating condition: {str(e)}")
            return False
            
    def _trigger_alert(self, rule: AlertRule, value: float, timestamp: float):
        """Trigger alert."""
        alert_key = f"{rule.name}_{int(timestamp)}"
        
        if alert_key not in self.active_alerts:
            alert = {
                "rule": rule.name,
                "metric": rule.metric,
                "value": value,
                "threshold": rule.threshold,
                "severity": rule.severity,
                "triggered_at": timestamp,
                "resolved_at": None,
                "notification_channels": rule.notification_channels
            }
            self.active_alerts[alert_key] = alert
            self.metrics.record_alert_triggered()
            self.logger.warning(f"Alert triggered: {rule.name} - {value} > {rule.threshold}")
            
            # Send notifications
            asyncio.create_task(self._send_notifications(alert))
            
    def resolve_alert(self, alert_key: str):
        """Resolve alert."""
        if alert_key in self.active_alerts:
            self.active_alerts[alert_key]["resolved_at"] = time.time()
            self.metrics.record_alert_resolved()
            self.logger.info(f"Alert resolved: {alert_key}")
            
    async def _send_notifications(self, alert: Dict[str, Any]):
        """Send alert notifications."""
        # Implementation would send to email, Slack, PagerDuty, etc.
        self.logger.info(f"Sending notification for alert: {alert['rule']}")


class DashboardManager:
    """Manages dashboards and real-time data."""
    
    def __init__(self):
        self.dashboards: Dict[str, DashboardConfig] = {}
        self.metrics = MonitoringMetrics()
        self.logger = logging.getLogger("aios.dashboards")
        
    def add_dashboard(self, config: DashboardConfig):
        """Add dashboard configuration."""
        self.dashboards[config.name] = config
        self.logger.info(f"Added dashboard: {config.name}")
        
    async def get_dashboard_data(self, dashboard_name: str) -> Dict[str, Any]:
        """Get dashboard data."""
        self.metrics.record_dashboard_request()
        
        if dashboard_name not in self.dashboards:
            return {"error": "Dashboard not found"}
            
        config = self.dashboards[dashboard_name]
        
        # Generate dashboard data
        data = {
            "name": config.name,
            "title": config.title,
            "refresh_interval": config.refresh_interval,
            "panels": [],
            "last_updated": time.time()
        }
        
        for panel in config.panels:
            panel_data = await self._generate_panel_data(panel)
            data["panels"].append(panel_data)
            
        return data
        
    async def _generate_panel_data(self, panel: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data for a single panel."""
        panel_type = panel.get("type", "metric")
        
        if panel_type == "metric":
            return {
                "id": panel["id"],
                "title": panel["title"],
                "type": "metric",
                "value": await self._get_metric_value(panel["metric"]),
                "unit": panel.get("unit", "")
            }
        elif panel_type == "chart":
            return {
                "id": panel["id"],
                "title": panel["title"],
                "type": "chart",
                "data": await self._get_chart_data(panel["metric"]),
                "chart_type": panel.get("chart_type", "line")
            }
        else:
            return {"id": panel["id"], "title": panel["title"], "type": "error", "error": "Unknown panel type"}
            
    async def _get_metric_value(self, metric_name: str) -> float:
        """Get current metric value."""
        # Implementation would query actual metrics
        return 0.0
        
    async def _get_chart_data(self, metric_name: str) -> List[Dict[str, Any]]:
        """Get chart data for a metric."""
        # Implementation would get historical data
        return [{"timestamp": time.time() - 3600, "value": 10.0}]


class MonitoringAPI:
    """Main API for monitoring and observability."""
    
    def __init__(self):
        self.alert_manager = AlertManager()
        self.dashboard_manager = DashboardManager()
        self.metrics = MonitoringMetrics()
        self.logger = logging.getLogger("aios.monitoring")
        
    def add_alert_rule(self, rule: AlertRule):
        """Add alert rule."""
        self.alert_manager.add_rule(rule)
        
    def add_dashboard(self, config: DashboardConfig):
        """Add dashboard."""
        self.dashboard_manager.add_dashboard(config)
        
    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health status."""
        health_score = 90.0  # Example score
        self.metrics.set_system_health(health_score)
        
        return {
            "health_score": health_score,
            "status": "healthy" if health_score > 80 else "degraded",
            "timestamp": time.time(),
            "active_alerts": len(self.alert_manager.active_alerts),
            "total_rules": len(self.alert_manager.rules)
        }
        
    async def get_alerts(self, active_only: bool = True) -> Dict[str, Any]:
        """Get alerts."""
        alerts = []
        
        for alert_key, alert in self.alert_manager.active_alerts.items():
            if active_only and alert["resolved_at"]:
                continue
            alerts.append(alert)
            
        return {
            "alerts": alerts,
            "total": len(alerts),
            "active": len([a for a in alerts if not a.get("resolved_at")])
        }
        
    async def get_dashboard(self, dashboard_name: str) -> Dict[str, Any]:
        """Get dashboard data."""
        return await self.dashboard_manager.get_dashboard_data(dashboard_name)
        
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "alerts_triggered": self.metrics.alerts_triggered.value,
            "alerts_resolved": self.metrics.alerts_resolved.value,
            "dashboard_requests": self.metrics.dashboard_requests.value,
            "api_response_time": {
                "avg": sum(self.metrics.api_response_time.values) / len(self.metrics.api_response_time.values) if self.metrics.api_response_time.values else 0,
                "max": max(self.metrics.api_response_time.values) if self.metrics.api_response_time.values else 0,
                "count": len(self.metrics.api_response_time.values)
            },
            "system_health": self.metrics.system_health.value
        }


def create_monitoring_app(monitoring_api: MonitoringAPI) -> Starlette:
    """Create Starlette application for monitoring."""
    
    async def health_endpoint(request: Request) -> JSONResponse:
        """Get system health."""
        try:
            health = await monitoring_api.get_system_health()
            return JSONResponse(health)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def alerts_endpoint(request: Request) -> JSONResponse:
        """Get alerts."""
        try:
            active_only = request.query_params.get("active_only", "true").lower() == "true"
            alerts = await monitoring_api.get_alerts(active_only)
            return JSONResponse(alerts)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def dashboard_endpoint(request: Request) -> JSONResponse:
        """Get dashboard."""
        try:
            dashboard_name = request.path_params.get("dashboard_name")
            dashboard = await monitoring_api.get_dashboard(dashboard_name)
            return JSONResponse(dashboard)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def metrics_endpoint(request: Request) -> JSONResponse:
        """Get metrics summary."""
        try:
            metrics = await monitoring_api.get_metrics_summary()
            return JSONResponse(metrics)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket for real-time monitoring."""
        await websocket.accept()
        
        try:
            while True:
                # Send real-time updates
                health = await monitoring_api.get_system_health()
                alerts = await monitoring_api.get_alerts()
                
                await websocket.send_text(json.dumps({
                    "type": "update",
                    "timestamp": time.time(),
                    "health": health,
                    "alerts": alerts
                }))
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
        except Exception as e:
            self.logger.error(f"WebSocket error: {str(e)}")
        finally:
            await websocket.close()
    
    routes = [
        Route("/health", health_endpoint),
        Route("/alerts", alerts_endpoint),
        Route("/dashboards/{dashboard_name}", dashboard_endpoint),
        Route("/metrics", metrics_endpoint),
        WebSocketRoute("/ws", websocket_endpoint),
    ]
    
    middleware = [
        # Add CORS middleware if needed
    ]
    
    return Starlette(routes=routes, middleware=middleware)


# Example usage
def setup_monitoring_system():
    """Setup monitoring system."""
    
    # Initialize monitoring API
    monitoring_api = MonitoringAPI()
    
    # Add alert rules
    alert_rule = AlertRule(
        name="high_cpu_usage",
        metric="cpu_usage",
        condition="value > 80",
        threshold=80,
        duration=300,  # 5 minutes
        severity="warning",
        notification_channels=["email", "slack"]
    )
    monitoring_api.add_alert_rule(alert_rule)
    
    # Add dashboard
    dashboard_config = DashboardConfig(
        name="system_overview",
        title="System Overview",
        refresh_interval=30,
        panels=[
            {
                "id": "cpu_panel",
                "title": "CPU Usage",
                "type": "metric",
                "metric": "cpu_usage",
                "unit": "%"
            },
            {
                "id": "memory_panel",
                "title": "Memory Usage",
                "type": "metric",
                "metric": "memory_usage",
                "unit": "%"
            },
            {
                "id": "response_time_panel",
                "title": "API Response Time",
                "type": "chart",
                "metric": "api_response_time",
                "chart_type": "line"
            }
        ]
    )
    monitoring_api.add_dashboard(dashboard_config)
    
    # Create Starlette app
    app = create_monitoring_app(monitoring_api)
    
    return app


if __name__ == "__main__":
    # Setup logging
    logger = setup_logging()
    
    # Setup monitoring
    app = setup_monitoring_system()
    
    print("Monitoring system initialized")
    print("Available endpoints:")
    print("  GET /health - Get system health")
    print("  GET /alerts - Get alerts")
    print("  GET /dashboards/{dashboard_name} - Get dashboard")
    print("  GET /metrics - Get metrics summary")
    print("  WebSocket /ws - Real-time monitoring updates")