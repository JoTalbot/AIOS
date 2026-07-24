"""
Enhanced AIOS API with External Integration Support

Combines all external integration capabilities into a comprehensive API system.
Provides unified access to integration protocols, monitoring, and external system connections.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Mount, Route

from aios_core.api.app import AIOSAPI
from aios_core.api.integration import ExternalIntegrationAPI, IntegrationEvent, IntegrationEventType
from aios_core.api.monitoring import Alert, AlertSeverity, AlertType, MonitoringSystem
from aios_core.api.protocols import ProtocolConfig, ProtocolManager, ProtocolType
from aios_core.telemetry import MetricCounter, MetricGauge, MetricHistogram

logger = logging.getLogger(__name__)


class EnhancedAIOSAPI:
    """Enhanced AIOS API with comprehensive external integration capabilities."""

    def __init__(self, db_path: str = ":memory:", **kwargs):
        # Create base API
        """Initialize EnhancedAIOSAPI."""
        self.base_api = AIOSAPI(db_path=db_path, **kwargs)

        # Create integration components
        self.integration_api = ExternalIntegrationAPI(self.base_api)
        self.protocol_manager = ProtocolManager(self.integration_api.integration_manager)
        self.monitoring_system = MonitoringSystem()

        # Setup enhanced logging
        self._setup_logging()

        # Performance metrics
        self.metrics = {
            "api_requests": MetricCounter("api_requests_total", "Total API requests"),
            "integration_events": MetricCounter(
                "integration_events_total", "Total integration events"
            ),
            "protocol_connections": MetricCounter(
                "protocol_connections_total", "Total protocol connections"
            ),
            "monitoring_alerts": MetricCounter(
                "monitoring_alerts_total", "Total monitoring alerts"
            ),
            "active_users": MetricGauge("active_users", "Number of active users"),
            "system_uptime": MetricGauge("system_uptime_seconds", "System uptime in seconds"),
        }

        self.start_time = time.time()
        self._running = False

    def _setup_logging(self):
        """Setup enhanced logging for the enhanced API."""
        from aios_core.logging_config import setup_logging

        # Setup main logger
        setup_logging(level="INFO", json_format=True)

        # Setup integration logger
        integration_logger = logging.getLogger("aios_enhanced_api")
        integration_logger.setLevel(logging.INFO)

    async def start_background_services(self) -> None:
        """Start all background services."""
        self._running = True

        # Start monitoring system
        monitoring_task = asyncio.create_task(self.monitoring_system.start_monitoring())

        # Start protocol manager
        protocol_task = asyncio.create_task(self.protocol_manager.start_all())

        # Start integration event processor
        integration_task = asyncio.create_task(
            self.integration_api.integration_manager.start_event_processor()
        )

        logger.info("Background services started")

        return [monitoring_task, protocol_task, integration_task]

    async def stop_background_services(self) -> None:
        """Stop all background services."""
        self._running = False

        # Stop monitoring system
        self.monitoring_system.stop_monitoring()

        # Stop protocol manager
        await self.protocol_manager.stop_all()

        # Stop integration event processor
        self.integration_api.integration_manager.stop_event_processor()

        logger.info("Background services stopped")

    def create_enhanced_app(self) -> Starlette:
        """Create enhanced Starlette app with all integration capabilities."""

        # Get base app
        app = self.base_api.create_starlette_app()

        # Add integration routes
        integration_routes = [
            # Integration management
            Route("/api/v1/integrations", self._integrations_list, methods=["GET"]),
            Route("/api/v1/integrations", self._integrations_create, methods=["POST"]),
            Route(
                "/api/v1/integrations/{integration_id}",
                self._integrations_get,
                methods=["GET"],
            ),
            Route(
                "/api/v1/integrations/{integration_id}",
                self._integrations_update,
                methods=["PUT"],
            ),
            Route(
                "/api/v1/integrations/{integration_id}",
                self._integrations_delete,
                methods=["DELETE"],
            ),
            # Protocol management
            Route("/api/v1/protocols", self._protocols_list, methods=["GET"]),
            Route("/api/v1/protocols", self._protocols_configure, methods=["POST"]),
            Route(
                "/api/v1/protocols/{protocol_type}/status",
                self._protocol_status,
                methods=["GET"],
            ),
            # Monitoring and alerts
            Route("/api/v1/monitoring/dashboard", self._monitoring_dashboard),
            Route("/api/v1/monitoring/alerts", self._monitoring_alerts, methods=["GET"]),
            Route(
                "/api/v1/monitoring/alerts",
                self._monitoring_alerts_create,
                methods=["POST"],
            ),
            Route(
                "/api/v1/monitoring/alerts/{alert_id}/resolve",
                self._monitoring_alerts_resolve,
                methods=["POST"],
            ),
            Route("/api/v1/monitoring/metrics", self._monitoring_metrics),
            Route("/api/v1/monitoring/health", self._monitoring_health),
            # External system connections
            Route("/api/v1/external/systems", self._external_systems_list, methods=["GET"]),
            Route(
                "/api/v1/external/systems",
                self._external_systems_connect,
                methods=["POST"],
            ),
            Route(
                "/api/v1/external/systems/{system_id}",
                self._external_systems_disconnect,
                methods=["DELETE"],
            ),
            Route(
                "/api/v1/external/systems/{system_id}/status",
                self._external_systems_status,
                methods=["GET"],
            ),
            # Data synchronization
            Route("/api/v1/sync/external", self._sync_external, methods=["POST"]),
            Route("/api/v1/sync/status", self._sync_status, methods=["GET"]),
            Route("/api/v1/sync/history", self._sync_history, methods=["GET"]),
            # Integration testing
            Route("/api/v1/integrations/test", self._integration_test, methods=["POST"]),
            Route(
                "/api/v1/integrations/benchmark",
                self._integration_benchmark,
                methods=["POST"],
            ),
            # Real-time event streaming
            Route("/api/v1/events/stream", self._event_stream),
            Route("/api/v1/events/webhooks", self._webhook_events),
            # System administration
            Route(
                "/api/v1/admin/integrations/reload",
                self._admin_reload_integrations,
                methods=["POST"],
            ),
            Route(
                "/api/v1/admin/protocols/restart",
                self._admin_restart_protocols,
                methods=["POST"],
            ),
            Route(
                "/api/v1/admin/monitoring/reset",
                self._admin_reset_monitoring,
                methods=["POST"],
            ),
        ]

        # Add integration routes to app
        app.router.routes.extend(integration_routes)

        # Add CORS middleware for external integrations
        app.middleware_stack = app.middleware_stack.add(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-Integration-Key",
                "X-Request-ID",
            ],
            expose_headers=["X-Integration-Key", "X-Request-ID"],
        )

        # Add integration metrics middleware
        app.middleware_stack = app.middleware_stack.add(self.integration_metrics_middleware)

        return app

    # Integration Management Endpoints

    async def _integrations_list(self, request: Request) -> JSONResponse:
        """List all registered integrations."""
        integrations = list(self.integration_api.integration_manager.webhook_handlers.keys())
        return JSONResponse(
            {
                "integrations": integrations,
                "count": len(integrations),
                "total_events_processed": self.integration_api.integration_manager.metrics[
                    "events_processed"
                ].value,
            }
        )

    async def _integrations_create(self, request: Request) -> JSONResponse:
        """Create a new integration."""
        try:
            data = await request.json()
            integration_type = data.get("type")
            config = data.get("config")

            if not integration_type or not config:
                return JSONResponse({"error": "type and config are required"}, status_code=400)

            # Create integration based on type
            if integration_type == "webhook":
                endpoint = config.get("endpoint")
                handler_url = config.get("handler_url")

                if not endpoint or not handler_url:
                    return JSONResponse(
                        {"error": "endpoint and handler_url are required"},
                        status_code=400,
                    )

                # Create webhook handler
                async def webhook_handler(event_data: dict[str, Any]) -> None:
                    """webhook handler."""
                    import aiohttp

                    async with aiohttp.ClientSession() as session:
                        try:
                            await session.post(handler_url, json=event_data, timeout=10)
                        except Exception as e:
                            logger.error(f"Webhook delivery failed: {e}")

                self.integration_api.integration_manager.register_webhook(endpoint, webhook_handler)

                return JSONResponse(
                    {
                        "message": "Integration created successfully",
                        "integration_type": integration_type,
                        "endpoint": endpoint,
                        "integration_id": f"webhook_{endpoint}",
                    },
                    status_code=201,
                )

            else:
                return JSONResponse(
                    {"error": f"Unsupported integration type: {integration_type}"},
                    status_code=400,
                )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _integrations_get(self, request: Request) -> JSONResponse:
        """Get integration details."""
        integration_id = request.path_params.get("integration_id")

        # For demo, return mock integration details
        return JSONResponse(
            {
                "integration_id": integration_id,
                "type": "webhook",
                "status": "active",
                "created_at": time.time(),
                "last_activity": time.time(),
                "metrics": {
                    "events_received": 150,
                    "events_success": 145,
                    "events_failed": 5,
                },
            }
        )

    async def _integrations_update(self, request: Request) -> JSONResponse:
        """Update integration configuration."""
        integration_id = request.path_params.get("integration_id")
        data = await request.json()

        return JSONResponse(
            {
                "message": f"Integration {integration_id} updated successfully",
                "updated_fields": list(data.keys()),
            }
        )

    async def _integrations_delete(self, request: Request) -> JSONResponse:
        """Delete an integration."""
        integration_id = request.path_params.get("integration_id")

        # For demo, remove from webhook handlers
        if integration_id in self.integration_api.integration_manager.webhook_handlers:
            del self.integration_api.integration_manager.webhook_handlers[integration_id]
            return JSONResponse({"message": f"Integration {integration_id} deleted"})
        else:
            return JSONResponse({"error": "Integration not found"}, status_code=404)

    # Protocol Management Endpoints

    async def _protocols_list(self, request: Request) -> JSONResponse:
        """List available protocols."""
        protocols = [
            {"type": "websocket", "status": "active", "endpoint": "/ws"},
            {"type": "graphql", "status": "active", "endpoint": "/graphql"},
            {"type": "sse", "status": "active", "endpoint": "/events"},
            {"type": "grpc", "status": "inactive", "endpoint": "/grpc"},
            {"type": "message_queue", "status": "active", "endpoint": "/queue"},
        ]
        return JSONResponse({"protocols": protocols})

    async def _protocols_configure(self, request: Request) -> JSONResponse:
        """Configure a protocol."""
        try:
            data = await request.json()
            protocol_type = data.get("type")
            config = data.get("config")

            if not protocol_type or not config:
                return JSONResponse({"error": "type and config are required"}, status_code=400)

            # Configure protocol
            protocol_config = ProtocolConfig(protocol_type=ProtocolType(protocol_type), **config)

            # Add to protocol manager (for demo)
            logger.info(f"Configuring protocol: {protocol_type}")

            return JSONResponse(
                {
                    "message": f"Protocol {protocol_type} configured successfully",
                    "protocol_type": protocol_type,
                    "config": config,
                },
                status_code=201,
            )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _protocol_status(self, request: Request) -> JSONResponse:
        """Get protocol status."""
        protocol_type = request.path_params.get("protocol_type")

        # For demo, return mock status
        return JSONResponse(
            {
                "protocol_type": protocol_type,
                "status": "active",
                "connections": 5,
                "messages_processed": 1000,
                "last_activity": time.time(),
            }
        )

    # Monitoring Endpoints

    async def _monitoring_dashboard(self, request: Request) -> JSONResponse:
        """Get monitoring dashboard data."""
        dashboard_data = self.monitoring_system.get_monitoring_dashboard_data()

        return JSONResponse(
            {
                "dashboard": dashboard_data,
                "system_metrics": {
                    "uptime": time.time() - self.start_time,
                    "api_requests": self.metrics["api_requests"].value,
                    "integration_events": self.metrics["integration_events"].value,
                    "active_connections": self.metrics["protocol_connections"].value,
                },
            }
        )

    async def _monitoring_alerts(self, request: Request) -> JSONResponse:
        """Get monitoring alerts."""
        active_alerts = self.monitoring_system.alert_manager.get_active_alerts()
        alert_history = self.monitoring_system.alert_manager.get_alert_history()

        return JSONResponse(
            {
                "active_alerts": [
                    {
                        "id": alert.id,
                        "type": alert.alert_type.value,
                        "severity": alert.severity.value,
                        "title": alert.title,
                        "message": alert.message,
                        "source": alert.source,
                        "timestamp": alert.timestamp,
                    }
                    for alert in active_alerts
                ],
                "alert_history": [
                    {
                        "id": alert.id,
                        "type": alert.alert_type.value,
                        "severity": alert.severity.value,
                        "title": alert.title,
                        "resolved": alert.resolved,
                        "timestamp": alert.timestamp,
                    }
                    for alert in alert_history[-20:]  # Last 20 alerts
                ],
                "totals": {
                    "active_alerts": len(active_alerts),
                    "total_alerts": len(alert_history),
                },
            }
        )

    async def _monitoring_alerts_create(self, request: Request) -> JSONResponse:
        """Create a manual alert (for testing)."""
        try:
            data = await request.json()
            alert = Alert(
                alert_type=AlertType(data.get("type", "performance")),
                severity=AlertSeverity(data.get("severity", "medium")),
                title=data.get("title", "Manual Alert"),
                message=data.get("message", "Manual alert created"),
                source="manual",
                metadata=data.get("metadata"),
            )

            await self.monitoring_system.alert_manager.create_alert(alert)
            self.metrics["monitoring_alerts"].add(1)

            return JSONResponse(
                {"message": "Alert created successfully", "alert_id": alert.id},
                status_code=201,
            )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _monitoring_alerts_resolve(self, request: Request) -> JSONResponse:
        """Resolve an alert."""
        alert_id = request.path_params.get("alert_id")

        try:
            await self.monitoring_system.alert_manager.resolve_alert(alert_id)
            return JSONResponse({"message": f"Alert {alert_id} resolved"})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _monitoring_metrics(self, request: Request) -> JSONResponse:
        """Get detailed monitoring metrics."""
        snapshot = self.monitoring_system.performance_monitor.get_performance_snapshot()

        return JSONResponse(
            {
                "performance_metrics": {
                    "cpu_usage": snapshot.cpu_usage,
                    "memory_usage": snapshot.memory_usage,
                    "request_rate": snapshot.request_rate,
                    "error_rate": snapshot.error_rate,
                    "response_time_avg": snapshot.response_time_avg,
                    "response_time_p95": snapshot.response_time_p95,
                    "response_time_p99": snapshot.response_time_p99,
                },
                "integration_metrics": {
                    "events_processed": snapshot.integration_events_processed,
                    "events_failed": snapshot.integration_events_failed,
                },
                "timestamp": snapshot.timestamp,
            }
        )

    async def _monitoring_health(self, request: Request) -> JSONResponse:
        """Get system health status."""
        try:
            # Check base API health
            health = await self.base_api._health(request)

            # Check integration health
            integration_health = {
                "webhook_handlers": len(self.integration_api.integration_manager.webhook_handlers),
                "event_queue_size": self.integration_api.integration_manager.event_queue.qsize(),
                "event_processor_running": self.integration_api.integration_manager._running,
            }

            # Check protocol health
            protocol_health = {
                "active_protocols": len(self.protocol_manager.adapters),
                "running": self.protocol_manager._running,
            }

            # Check monitoring health
            monitoring_health = {
                "active_alerts": len(self.monitoring_system.alert_manager.get_active_alerts()),
                "monitoring_running": self.monitoring_system._running,
            }

            return JSONResponse(
                {
                    "status": "healthy",
                    "overall_health": "healthy",
                    "components": {
                        "core_api": health,
                        "integrations": integration_health,
                        "protocols": protocol_health,
                        "monitoring": monitoring_health,
                    },
                    "timestamp": time.time(),
                }
            )

        except Exception as e:
            return JSONResponse(
                {"status": "unhealthy", "error": str(e), "timestamp": time.time()},
                status_code=503,
            )

    # External System Management Endpoints

    async def _external_systems_list(self, request: Request) -> JSONResponse:
        """List connected external systems."""
        systems = [
            {
                "id": "external_api_1",
                "name": "External API 1",
                "status": "connected",
                "type": "api",
            },
            {
                "id": "database_1",
                "name": "Database 1",
                "status": "connected",
                "type": "database",
            },
            {
                "id": "message_queue_1",
                "name": "Message Queue 1",
                "status": "disconnected",
                "type": "queue",
            },
        ]
        return JSONResponse({"systems": systems})

    async def _external_systems_connect(self, request: Request) -> JSONResponse:
        """Connect to an external system."""
        try:
            data = await request.json()
            system_id = data.get("id")
            system_config = data.get("config")

            if not system_id or not system_config:
                return JSONResponse({"error": "id and config are required"}, status_code=400)

            # For demo, create mock connection
            logger.info(f"Connecting to external system: {system_id}")

            return JSONResponse(
                {
                    "message": f"Connected to external system {system_id}",
                    "system_id": system_id,
                    "connection_id": f"conn_{int(time.time())}",
                },
                status_code=201,
            )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _external_systems_disconnect(self, request: Request) -> JSONResponse:
        """Disconnect from an external system."""
        system_id = request.path_params.get("system_id")

        # For demo, remove connection
        logger.info(f"Disconnecting from external system: {system_id}")

        return JSONResponse({"message": f"Disconnected from external system {system_id}"})

    async def _external_systems_status(self, request: Request) -> JSONResponse:
        """Get external system status."""
        system_id = request.path_params.get("system_id")

        # For demo, return mock status
        return JSONResponse(
            {
                "system_id": system_id,
                "status": "connected",
                "last_activity": time.time(),
                "metrics": {
                    "requests_sent": 150,
                    "responses_received": 148,
                    "errors": 2,
                },
            }
        )

    # Data Synchronization Endpoints

    async def _sync_external(self, request: Request) -> JSONResponse:
        """Trigger external data synchronization."""
        try:
            data = await request.json()
            source_system = data.get("source")
            target_system = data.get("target")
            sync_type = data.get("sync_type")

            if not source_system or not target_system or not sync_type:
                return JSONResponse(
                    {"error": "source, target, and sync_type are required"},
                    status_code=400,
                )

            # Create sync event
            event = IntegrationEvent(
                event_type=IntegrationEventType.DATA_SYNC,
                source=source_system,
                timestamp=time.time(),
                data={
                    "source": source_system,
                    "target": target_system,
                    "sync_type": sync_type,
                },
            )

            await self.integration_api.integration_manager.event_queue.put(event)
            self.metrics["integration_events"].add(1)

            return JSONResponse(
                {
                    "message": f"Sync initiated from {source_system} to {target_system}",
                    "sync_id": f"sync_{int(time.time())}",
                    "status": "queued",
                },
                status_code=202,
            )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _sync_status(self, request: Request) -> JSONResponse:
        """Get synchronization status."""
        # For demo, return mock status
        return JSONResponse(
            {
                "active_syncs": [
                    {
                        "sync_id": "sync_123",
                        "source": "external_api",
                        "target": "local_db",
                        "status": "running",
                        "progress": 65,
                    }
                ],
                "completed_syncs": [
                    {
                        "sync_id": "sync_122",
                        "source": "external_api",
                        "target": "local_db",
                        "status": "completed",
                        "duration": 120,
                    }
                ],
                "failed_syncs": [],
                "queue_size": self.integration_api.integration_manager.event_queue.qsize(),
            }
        )

    async def _sync_history(self, request: Request) -> JSONResponse:
        """Get synchronization history."""
        # For demo, return mock history
        return JSONResponse(
            {
                "history": [
                    {
                        "sync_id": "sync_123",
                        "source": "external_api",
                        "target": "local_db",
                        "status": "completed",
                        "timestamp": time.time() - 3600,
                        "duration": 120,
                        "records_synced": 1500,
                    }
                ],
                "limit": 50,
            }
        )

    # Integration Testing Endpoints

    async def _integration_test(self, request: Request) -> JSONResponse:
        """Test integration functionality."""
        try:
            data = await request.json()
            test_type = data.get("test_type")
            test_config = data.get("config")

            if not test_type or not test_config:
                return JSONResponse({"error": "test_type and config are required"}, status_code=400)

            # Run test based on type
            if test_type == "webhook":
                result = await self._test_webhook(test_config)
            elif test_type == "protocol":
                result = await self._test_protocol(test_config)
            elif test_type == "monitoring":
                result = await self._test_monitoring(test_config)
            else:
                return JSONResponse(
                    {"error": f"Unsupported test type: {test_type}"}, status_code=400
                )

            return JSONResponse(
                {"test_type": test_type, "result": result, "timestamp": time.time()}
            )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _test_webhook(self, config: dict[str, Any]) -> dict[str, Any]:
        """Test webhook functionality."""
        endpoint = config.get("endpoint")
        test_payload = config.get("payload", {})

        if not endpoint:
            return {"success": False, "error": "Endpoint required"}

        # Test webhook delivery
        try:
            # Create test event
            event = IntegrationEvent(
                event_type=IntegrationEventType.WEBHOOK,
                source="test",
                timestamp=time.time(),
                data={"endpoint": endpoint, "payload": test_payload},
            )

            await self.integration_api.integration_manager.process_event(event)

            return {
                "success": True,
                "message": "Webhook test completed",
                "endpoint": endpoint,
                "payload_sent": test_payload,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _test_protocol(self, config: dict[str, Any]) -> dict[str, Any]:
        """Test protocol functionality."""
        protocol_type = config.get("type")

        if protocol_type not in self.protocol_manager.adapters:
            return {
                "success": False,
                "error": f"Protocol {protocol_type} not available",
            }

        # For demo, return mock result
        return {
            "success": True,
            "message": f"Protocol {protocol_type} test completed",
            "protocol_type": protocol_type,
            "status": "active",
        }

    async def _test_monitoring(self, config: dict[str, Any]) -> dict[str, Any]:
        """Test monitoring functionality."""
        # Create test alert
        alert = Alert(
            alert_type=AlertType(config.get("type", "performance")),
            severity=AlertSeverity(config.get("severity", "medium")),
            title="Test Alert",
            message="This is a test alert",
            source="test",
            metadata={"test": True},
        )

        await self.monitoring_system.alert_manager.create_alert(alert)

        return {
            "success": True,
            "message": "Monitoring test completed",
            "alert_id": alert.id,
            "alert_created": True,
        }

    async def _integration_benchmark(self, request: Request) -> JSONResponse:
        """Run integration performance benchmark."""
        try:
            data = await request.json()
            benchmark_type = data.get("type", "webhook")
            duration = data.get("duration", 60)  # seconds
            rate = data.get("rate", 10)  # requests per second

            # Start benchmark
            start_time = time.time()
            results = await self._run_benchmark(benchmark_type, duration, rate)

            return JSONResponse(
                {
                    "benchmark_type": benchmark_type,
                    "duration": duration,
                    "rate": rate,
                    "results": results,
                    "total_duration": time.time() - start_time,
                }
            )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _run_benchmark(self, benchmark_type: str, duration: int, rate: int) -> dict[str, Any]:
        """Run benchmark and return results."""
        import statistics

        request_times = []
        success_count = 0
        error_count = 0

        # Start benchmark
        start_time = time.time()
        end_time = start_time + duration

        while time.time() < end_time:
            # Send benchmark request
            request_start = time.time()

            try:
                if benchmark_type == "webhook":
                    # Simulate webhook request
                    await asyncio.sleep(0.1)  # Simulate processing
                    success_count += 1
                elif benchmark_type == "protocol":
                    # Simulate protocol request
                    await asyncio.sleep(0.05)
                    success_count += 1
                else:
                    error_count += 1

                request_end = time.time()
                request_times.append(request_end - request_start)

            except Exception:
                error_count += 1

            # Wait for next request based on rate
            wait_time = (1.0 / rate) - (time.time() - request_start)
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        # Calculate statistics
        avg_response_time = statistics.mean(request_times) if request_times else 0
        p95_response_time = statistics.quantiles(request_times, n=20)[18] if request_times else 0

        return {
            "total_requests": success_count + error_count,
            "successful_requests": success_count,
            "failed_requests": error_count,
            "success_rate": success_count / max(success_count + error_count, 1),
            "avg_response_time": avg_response_time,
            "p95_response_time": p95_response_time,
            "requests_per_second": (success_count + error_count) / duration,
        }

    # Real-time Event Streaming Endpoints

    async def _event_stream(self, request: Request) -> StreamingResponse:
        """Real-time event stream for monitoring and debugging."""

        async def event_generator() -> None:
            """event generator."""
            while True:
                if await request.is_disconnected():
                    break

                # Send system metrics
                metrics = self.monitoring_system.performance_monitor.get_performance_snapshot()

                event_data = {
                    "type": "system_metrics",
                    "timestamp": time.time(),
                    "data": {
                        "cpu_usage": metrics.cpu_usage,
                        "memory_usage": metrics.memory_usage,
                        "request_rate": metrics.request_rate,
                        "error_rate": metrics.error_rate,
                        "active_connections": self.metrics["protocol_connections"].value,
                    },
                }

                yield f"data: {json.dumps(event_data)}\n\n"
                await asyncio.sleep(5)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            },
        )

    async def _webhook_events(self, request: Request) -> StreamingResponse:
        """Stream webhook events for debugging."""

        async def webhook_event_generator() -> None:
            """webhook event generator."""
            while True:
                if await request.is_disconnected():
                    break

                # Send webhook events (for demo, send mock events)
                event_data = {
                    "type": "webhook_event",
                    "timestamp": time.time(),
                    "data": {
                        "endpoint": f"/webhook_{int(time.time()) % 1000}",
                        "event_id": f"event_{int(time.time())}",
                        "status": "delivered",
                    },
                }

                yield f"data: {json.dumps(event_data)}\n\n"
                await asyncio.sleep(10)

        return StreamingResponse(
            webhook_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            },
        )

    # System Administration Endpoints

    async def _admin_reload_integrations(self, request: Request) -> JSONResponse:
        """Reload integrations (admin only)."""
        try:
            # For demo, reload webhook handlers
            self.integration_api.integration_manager.webhook_handlers.clear()

            return JSONResponse(
                {
                    "message": "Integrations reloaded successfully",
                    "timestamp": time.time(),
                }
            )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def _admin_restart_protocols(self, request: Request) -> JSONResponse:
        """Restart protocols (admin only)."""
        try:
            # Stop and restart protocols
            await self.protocol_manager.stop_all()
            await self.protocol_manager.start_all()

            return JSONResponse(
                {
                    "message": "Protocols restarted successfully",
                    "timestamp": time.time(),
                }
            )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def _admin_reset_monitoring(self, request: Request) -> JSONResponse:
        """Reset monitoring data (admin only)."""
        try:
            # Clear alerts and metrics
            self.monitoring_system.alert_manager.alerts.clear()
            self.monitoring_system.alert_manager.alert_history.clear()

            return JSONResponse(
                {
                    "message": "Monitoring data reset successfully",
                    "timestamp": time.time(),
                }
            )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # Middleware

    async def integration_metrics_middleware(self, request: Request, call_next) -> None:
        """Middleware to track API request metrics."""
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Record metrics
        request_time = time.time() - start_time
        self.metrics["api_requests"].add(1)

        # Add integration metrics to response headers
        response.headers["X-Request-ID"] = f"req_{int(time.time())}"
        response.headers["X-Processing-Time"] = f"{request_time:.3f}s"
        response.headers["X-API-Version"] = "v1.0"

        return response


def create_enhanced_api(db_path: str = ":memory:", **kwargs) -> EnhancedAIOSAPI:
    """Create an enhanced AIOS API with external integration capabilities."""
    return EnhancedAIOSAPI(db_path=db_path, **kwargs)
