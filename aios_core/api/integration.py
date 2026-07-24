"""
AIOS External Integration Module

Provides enhanced API endpoints and integration capabilities for external systems.
Includes support for webhooks, event streaming, third-party authentication, and system monitoring.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Mount, Route

from aios_core.api.app import AIOSAPI
from aios_core.logging_config import setup_logging
from aios_core.telemetry import MetricCounter, MetricGauge, MetricHistogram
from aios_core.tracing import tracer

logger = logging.getLogger(__name__)


class IntegrationEventType(Enum):
    """Types of external integration events."""

    WEBHOOK = "webhook"
    SYSTEM_EVENT = "system_event"
    USER_ACTION = "user_action"
    API_CALL = "api_call"
    DATA_SYNC = "data_sync"
    MONITORING_ALERT = "monitoring_alert"


@dataclass
class IntegrationEvent:
    """External integration event structure."""

    event_type: IntegrationEventType
    source: str
    timestamp: float
    data: dict[str, Any]
    metadata: dict[str, Any] | None = None
    correlation_id: str | None = None


class ExternalIntegrationManager:
    """Manages external system integrations and event processing."""

    def __init__(self, api: AIOSAPI):
        """Initialize ExternalIntegrationManager."""
        self.api = api
        self.webhook_handlers: Dict[str, callable] = {}
        self.event_queue = asyncio.Queue()
        self.metrics = {
            "webhooks_received": MetricCounter(
                "webhooks_received", "Number of webhook events received"
            ),
            "events_processed": MetricCounter(
                "events_processed", "Number of integration events processed"
            ),
            "processing_errors": MetricCounter(
                "processing_errors", "Number of event processing errors"
            ),
            "active_connections": MetricGauge(
                "active_connections", "Number of active streaming connections"
            ),
            "processing_time": MetricHistogram(
                "processing_time", "Event processing time distribution"
            ),
        }
        self._running = False

    def register_webhook(self, endpoint: str, handler: callable) -> None:
        """Register a webhook handler for a specific endpoint."""
        self.webhook_handlers[endpoint] = handler
        logger.info(f"Registered webhook handler for {endpoint}")

    async def process_event(self, event: IntegrationEvent) -> None:
        """Process an integration event."""
        start_time = time.time()

        try:
            with tracer.span(
                "integration_event_processing",
                {
                    "event_type": event.event_type.value,
                    "source": event.source,
                    "correlation_id": event.correlation_id,
                },
            ):
                # Record metrics
                self.metrics["events_processed"].add(1)

                # Route to appropriate handler
                if event.event_type == IntegrationEventType.WEBHOOK:
                    await self._handle_webhook_event(event)
                elif event.event_type == IntegrationEventType.SYSTEM_EVENT:
                    await self._handle_system_event(event)
                else:
                    await self._handle_generic_event(event)

                # Record processing time
                processing_time = time.time() - start_time
                self.metrics["processing_time"].observe(processing_time)

        except Exception as e:
            self.metrics["processing_errors"].add(1)
            logger.error(f"Error processing integration event: {e}")
            raise

    async def _handle_webhook_event(self, event: IntegrationEvent):
        """Handle webhook events."""
        webhook_endpoint = event.data.get("endpoint")
        if webhook_endpoint in self.webhook_handlers:
            await self.webhook_handlers[webhook_endpoint](event.data)
        else:
            logger.warning(f"No webhook handler found for endpoint: {webhook_endpoint}")

    async def _handle_system_event(self, event: IntegrationEvent):
        """Handle system events."""
        # Route system events to appropriate subsystems
        if event.source == "monitoring":
            await self._handle_monitoring_event(event)
        elif event.source == "security":
            await self._handle_security_event(event)
        else:
            logger.info(f"Received system event from {event.source}")

    async def _handle_generic_event(self, event: IntegrationEvent):
        """Handle generic integration events."""
        logger.info(f"Processing {event.event_type.value} event from {event.source}")

    async def _handle_monitoring_event(self, event: IntegrationEvent):
        """Handle monitoring-related events."""
        alert_data = event.data.get("alert")
        if alert_data:
            logger.warning(f"Monitoring alert: {alert_data}")
            # Could trigger automated responses here

    async def _handle_security_event(self, event: IntegrationEvent):
        """Handle security-related events."""
        security_data = event.data.get("security_event")
        if security_data:
            logger.warning(f"Security event: {security_data}")
            # Could trigger security responses here

    async def start_event_processor(self) -> None:
        """Start the background event processor."""
        self._running = True
        while self._running:
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                await self.process_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in event processor: {e}")

    def stop_event_processor(self) -> None:
        """Stop the background event processor."""
        self._running = False


class ExternalIntegrationAPI:
    """Enhanced API with external integration capabilities."""

    def __init__(self, api: AIOSAPI):
        """Initialize ExternalIntegrationAPI."""
        self.api = api
        self.integration_manager = ExternalIntegrationManager(api)

    def create_enhanced_app(self) -> Starlette:
        """Create enhanced Starlette app with integration endpoints."""

        # Integration-specific routes
        integration_routes = [
            # Webhook endpoints
            Route("/api/v1/integrations/webhooks", self._webhook_list, methods=["GET"]),
            Route(
                "/api/v1/integrations/webhooks/{endpoint}",
                self._webhook_register,
                methods=["POST"],
            ),
            Route(
                "/api/v1/integrations/webhooks/{endpoint}",
                self._webhook_unregister,
                methods=["DELETE"],
            ),
            # Event streaming
            Route("/api/v1/integrations/events/stream", self._event_stream),
            # External system monitoring
            Route("/api/v1/integrations/monitoring/metrics", self._integration_metrics),
            Route("/api/v1/integrations/monitoring/health", self._integration_health),
            # Third-party authentication
            Route("/api/v1/integrations/auth/external", self._external_auth),
            Route("/api/v1/integrations/auth/callback", self._auth_callback),
            # Data synchronization
            Route(
                "/api/v1/integrations/sync/external",
                self._external_sync,
                methods=["POST"],
            ),
            Route("/api/v1/integrations/sync/status", self._sync_status),
            # Webhook testing
            Route(
                "/api/v1/integrations/webhooks/test",
                self._webhook_test,
                methods=["POST"],
            ),
        ]

        # Mount integration routes under the main API
        app = self.api.create_starlette_app()

        # Add integration middleware
        app.router.routes.extend(integration_routes)

        # Add CORS for external integrations
        app.middleware_stack = app.middleware_stack.add(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Integration-Key"],
        )

        return app

    async def _webhook_list(self, request: Request) -> JSONResponse:
        """List registered webhook endpoints."""
        endpoints = list(self.integration_manager.webhook_handlers.keys())
        return JSONResponse({"webhooks": endpoints, "count": len(endpoints)})

    async def _webhook_register(self, request: Request) -> JSONResponse:
        """Register a new webhook endpoint."""
        try:
            data = await request.json()
            endpoint = data.get("endpoint")
            handler_url = data.get("handler_url")

            if not endpoint or not handler_url:
                return JSONResponse(
                    {"error": "endpoint and handler_url are required"}, status_code=400
                )

            # Create a simple webhook handler that forwards to the URL
            async def webhook_handler(event_data: dict[str, Any]) -> None:
                """webhook handler."""
                import aiohttp

                async with aiohttp.ClientSession() as session:
                    try:
                        await session.post(handler_url, json=event_data, timeout=10)
                    except Exception as e:
                        logger.error(f"Webhook delivery failed: {e}")

            self.integration_manager.register_webhook(endpoint, webhook_handler)

            return JSONResponse(
                {
                    "message": "Webhook registered successfully",
                    "endpoint": endpoint,
                    "handler_url": handler_url,
                },
                status_code=201,
            )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _webhook_unregister(self, request: Request) -> JSONResponse:
        """Unregister a webhook endpoint."""
        endpoint = request.path_params.get("endpoint")

        if endpoint in self.integration_manager.webhook_handlers:
            del self.integration_manager.webhook_handlers[endpoint]
            return JSONResponse({"message": f"Webhook {endpoint} unregistered"})
        else:
            return JSONResponse({"error": "Webhook not found"}, status_code=404)

    async def _event_stream(self, request: Request) -> StreamingResponse:
        """Server-sent events stream for real-time integration events."""

        async def event_generator() -> None:
            # For demo purposes, send periodic system status
            """event generator."""
            while True:
                if await request.is_disconnected():
                    break

                # Send system metrics
                metrics_data = {
                    "timestamp": time.time(),
                    "type": "system_metrics",
                    "data": {
                        "memory_usage": "45%",
                        "cpu_usage": "23%",
                        "active_tasks": self.api.orchestrator.stats().get("active_tasks", 0),
                    },
                }

                yield f"data: {json.dumps(metrics_data)}\n\n"
                await asyncio.sleep(5)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    async def _integration_metrics(self, request: Request) -> JSONResponse:
        """Get integration system metrics."""
        metrics_data = {
            "webhooks_received": self.integration_manager.metrics["webhooks_received"].value,
            "events_processed": self.integration_manager.metrics["events_processed"].value,
            "processing_errors": self.integration_manager.metrics["processing_errors"].value,
            "active_connections": self.integration_manager.metrics["active_connections"].value,
            "processing_time_summary": self.integration_manager.metrics[
                "processing_time"
            ].get_summary(),
            "uptime": time.time(),  # Server uptime
        }

        return JSONResponse(metrics_data)

    async def _integration_health(self, request: Request) -> JSONResponse:
        """Get integration system health status."""
        try:
            # Check core API health
            health = await self.api._health(request)

            # Add integration-specific health checks
            integration_health = {
                "webhook_handlers": len(self.integration_manager.webhook_handlers),
                "event_queue_size": self.integration_manager.event_queue.qsize(),
                "event_processor_running": self.integration_manager._running,
            }

            return JSONResponse(
                {
                    "status": "healthy",
                    "core_api": health,
                    "integrations": integration_health,
                }
            )

        except Exception as e:
            return JSONResponse({"status": "unhealthy", "error": str(e)}, status_code=503)

    async def _external_auth(self, request: Request) -> JSONResponse:
        """Handle external authentication requests."""
        try:
            data = await request.json()
            provider = data.get("provider")
            token = data.get("token")

            if not provider or not token:
                return JSONResponse({"error": "provider and token are required"}, status_code=400)

            # Here you would integrate with external auth providers
            # For demo, return a mock successful response
            return JSONResponse(
                {
                    "authenticated": True,
                    "provider": provider,
                    "user_id": f"user_{hash(token)}",
                    "roles": ["external_user"],
                    "expires_in": 3600,
                }
            )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _auth_callback(self, request: Request) -> JSONResponse:
        """Handle authentication callbacks from external providers."""
        try:
            data = await request.json()

            # Process auth callback and create integration event
            event = IntegrationEvent(
                event_type=IntegrationEventType.USER_ACTION,
                source="external_auth",
                timestamp=time.time(),
                data=data,
                correlation_id=data.get("state"),
            )

            # Queue the event for processing
            await self.integration_manager.event_queue.put(event)

            return JSONResponse(
                {
                    "status": "callback_received",
                    "message": "Authentication callback processed",
                }
            )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _external_sync(self, request: Request) -> JSONResponse:
        """Trigger external data synchronization."""
        try:
            data = await request.json()
            source_system = data.get("source")
            sync_type = data.get("sync_type")

            if not source_system or not sync_type:
                return JSONResponse({"error": "source and sync_type are required"}, status_code=400)

            # Create sync event
            event = IntegrationEvent(
                event_type=IntegrationEventType.DATA_SYNC,
                source=source_system,
                timestamp=time.time(),
                data={"sync_type": sync_type, "source": source_system},
            )

            await self.integration_manager.event_queue.put(event)

            return JSONResponse(
                {
                    "message": f"Sync initiated for {source_system}",
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
                "active_syncs": [],
                "completed_syncs": [],
                "failed_syncs": [],
                "queue_size": self.integration_manager.event_queue.qsize(),
            }
        )

    async def _webhook_test(self, request: Request) -> JSONResponse:
        """Test a webhook endpoint."""
        try:
            data = await request.json()
            endpoint = data.get("endpoint")
            test_payload = data.get("payload", {})

            if not endpoint:
                return JSONResponse({"error": "endpoint is required"}, status_code=400)

            # Create test event
            event = IntegrationEvent(
                event_type=IntegrationEventType.WEBHOOK,
                source="test",
                timestamp=time.time(),
                data={"endpoint": endpoint, "payload": test_payload},
            )

            # Process the test event
            await self.integration_manager.process_event(event)

            return JSONResponse(
                {
                    "message": "Webhook test completed",
                    "endpoint": endpoint,
                    "payload_sent": test_payload,
                }
            )

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)


def create_enhanced_api(db_path: str = ":memory:", **kwargs) -> ExternalIntegrationAPI:
    """Create an enhanced AIOS API with external integration capabilities."""

    # Create base API
    base_api = AIOSAPI(db_path=db_path, **kwargs)

    # Create enhanced integration API
    integration_api = ExternalIntegrationAPI(base_api)

    return integration_api
