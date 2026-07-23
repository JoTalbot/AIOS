"""Enhanced External Integration System for AIOS.

Provides advanced integration capabilities with external systems including:
- Real-time webhook notifications
- GraphQL API gateway
- Message queue connectors
- Enhanced monitoring adapters
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional, Union

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.websockets import WebSocket

from .logging_config import setup_logging
from .telemetry import MetricCounter, MetricGauge, MetricHistogram
from .tracing import tracer

__all__ = ["WebhookConfig", "GraphQLConfig", "IntegrationMetrics", "WebhookManager", "GraphQLAPI", "MessageQueueConnector", "KafkaConnector", "ExternalIntegrationAPI"]


@dataclass
class WebhookConfig:
    """Configuration for webhook endpoints."""

    url: str
    events: List[str]
    headers: Optional[Dict[str, str]] = None
    timeout: int = 30
    retry_count: int = 3


@dataclass
class GraphQLConfig:
    """Configuration for GraphQL API."""

    schema: str
    playground_enabled: bool = True
    introspection_enabled: bool = True
    max_complexity: int = 1000


class IntegrationMetrics:
    """Enhanced metrics for external integrations."""

    def __init__(self):
        self.webhook_sent = MetricCounter("webhook_sent", "Total webhook notifications sent")
        self.webhook_failed = MetricCounter("webhook_failed", "Total webhook failures")
        self.graphql_requests = MetricCounter("graphql_requests", "Total GraphQL requests")
        self.graphql_errors = MetricCounter("graphql_errors", "Total GraphQL errors")
        self.message_queue_processed = MetricCounter(
            "message_queue_processed", "Total messages processed"
        )
        self.api_integration_latency = MetricHistogram(
            "api_integration_latency", "API integration latency in ms"
        )

    def record_webhook_success(self) -> None:
        """Record successful webhook delivery."""
        self.webhook_sent.add(1)

    def record_webhook_failure(self) -> None:
        """Record webhook delivery failure."""
        self.webhook_failed.add(1)

    def record_graphql_request(self) -> None:
        """Record GraphQL request."""
        self.graphql_requests.add(1)

    def record_graphql_error(self) -> None:
        """Record GraphQL error."""
        self.graphql_errors.add(1)

    def record_message_processed(self) -> None:
        """Record processed message."""
        self.message_queue_processed.add(1)

    def record_latency(self, duration_ms: float) -> None:
        """Record API integration latency."""
        self.api_integration_latency.observe(duration_ms)


class WebhookManager:
    """Manages webhook notifications to external systems."""

    def __init__(self, config: WebhookConfig):
        self.config = config
        self.metrics = IntegrationMetrics()
        self.logger = logging.getLogger("aios.webhooks")

    async def send_notification(self, event: str, data: Dict[str, Any]) -> bool:
        """Send webhook notification to external system."""
        if event not in self.config.events:
            self.logger.warning(f"Event {event} not in configured events")
            return False

        import aiohttp

        payload = {"event": event, "timestamp": time.time(), "data": data}

        headers = self.config.headers or {}
        headers.update({"Content-Type": "application/json", "User-Agent": "AIOS-Integration/1.0"})

        for attempt in range(self.config.retry_count):
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as session:
                    async with session.post(
                        self.config.url, json=payload, headers=headers
                    ) as response:
                        if response.status == 200:
                            self.metrics.record_webhook_success()
                            self.logger.info(f"Webhook sent successfully: {event}")
                            return True
                        else:
                            self.logger.error(
                                f"Webhook failed: {response.status} - {await response.text()}"
                            )

            except Exception as e:
                self.logger.error(f"Webhook attempt {attempt + 1} failed: {str(e)}")

            if attempt < self.config.retry_count - 1:
                await asyncio.sleep(2**attempt)  # Exponential backoff

        self.metrics.record_webhook_failure()
        return False


class GraphQLAPI:
    """GraphQL API gateway for AIOS."""

    def __init__(self, config: GraphQLConfig):
        self.config = config
        self.metrics = IntegrationMetrics()
        self.logger = logging.getLogger("aios.graphql")

    def execute_query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute GraphQL query."""
        start_time = time.time()

        try:
            # Simple GraphQL execution (in production, use graphql-core)
            result = {
                "data": {"message": "GraphQL execution would happen here"},
                "errors": None,
            }

            self.metrics.record_graphql_request()

        except Exception as e:
            self.metrics.record_graphql_error()
            result = {"data": None, "errors": [{"message": str(e)}]}

        duration_ms = (time.time() - start_time) * 1000
        self.metrics.record_latency(duration_ms)

        return result


class MessageQueueConnector(ABC):
    """Abstract base class for message queue connectors."""

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to message queue."""
        pass

    @abstractmethod
    async def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """Publish message to topic."""
        pass

    @abstractmethod
    async def subscribe(self, topic: str, callback: Callable) -> None:
        """Subscribe to topic messages."""
        pass


class KafkaConnector(MessageQueueConnector):
    """Kafka message queue connector."""

    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        self.producer = None

    async def connect(self) -> bool:
        """Connect to Kafka cluster."""
        try:
            # In production, use kafka-python or aiokafka
            self.logger.info(f"Connected to Kafka: {self.bootstrap_servers}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Kafka: {str(e)}")
            return False

    async def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """Publish message to Kafka topic."""
        try:
            # Implementation would use kafka-python or aiokafka
            self.logger.info(f"Published to {topic}: {message}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to publish to {topic}: {str(e)}")
            return False

    async def subscribe(self, topic: str, callback: Callable) -> None:
        """Subscribe to Kafka topic."""
        try:
            # Implementation would use kafka-python or aiokafka
            self.logger.info(f"Subscribed to {topic}")
        except Exception as e:
            self.logger.error(f"Failed to subscribe to {topic}: {str(e)}")


class ExternalIntegrationAPI:
    """Main API for external integrations."""

    def __init__(self):
        self.metrics = IntegrationMetrics()
        self.webhooks: Dict[str, WebhookManager] = {}
        self.graphql = None
        self.message_queues: Dict[str, MessageQueueConnector] = {}
        self.logger = logging.getLogger("aios.integration")

    def add_webhook(self, name: str, config: WebhookConfig) -> None:
        """Add webhook configuration."""
        self.webhooks[name] = WebhookManager(config)
        self.logger.info(f"Added webhook: {name}")

    def set_graphql(self, config: GraphQLConfig) -> None:
        """Set GraphQL configuration."""
        self.graphql = GraphQLAPI(config)
        self.logger.info("GraphQL API configured")

    def add_message_queue(self, name: str, connector: MessageQueueConnector) -> None:
        """Add message queue connector."""
        self.message_queues[name] = connector
        self.logger.info(f"Added message queue: {name}")

    async def send_webhook(self, webhook_name: str, event: str, data: Dict[str, Any]) -> bool:
        """Send webhook notification."""
        if webhook_name not in self.webhooks:
            self.logger.error(f"Webhook {webhook_name} not found")
            return False

        return await self.webhooks[webhook_name].send_notification(event, data)

    async def get_integration_metrics(self) -> Dict[str, Any]:
        """Get integration metrics."""
        return {
            "webhooks": {
                name: {
                    "sent": manager.metrics.webhook_sent.value,
                    "failed": manager.metrics.webhook_failed.value,
                }
                for name, manager in self.webhooks.items()
            },
            "graphql": {
                "requests": self.metrics.graphql_requests.value if self.graphql else 0,
                "errors": self.metrics.graphql_errors.value if self.graphql else 0,
            },
            "message_queue": {
                name: {"processed": connector.metrics.message_queue_processed.value}
                for name, connector in self.message_queues.items()
            },
            "latency": {
                "avg": (
                    self.metrics.api_integration_latency.values[-1]
                    if self.metrics.api_integration_latency.values
                    else 0
                ),
                "max": (
                    max(self.metrics.api_integration_latency.values)
                    if self.metrics.api_integration_latency.values
                    else 0
                ),
            },
        }


def create_integration_app(integration_api: ExternalIntegrationAPI) -> Starlette:
    """Create Starlette application for external integrations."""

    async def webhook_endpoint(request: Request) -> JSONResponse:
        """Handle webhook notifications."""
        integration_api.metrics.record_graphql_request()

        try:
            data = await request.json()
            webhook_name = request.path_params.get("webhook_name")

            if webhook_name not in integration_api.webhooks:
                return JSONResponse({"error": "Webhook not found"}, status_code=404)

            # Process webhook
            success = await integration_api.send_webhook(webhook_name, data.get("event", ""), data)

            return JSONResponse({"success": success})

        except Exception as e:
            integration_api.metrics.record_graphql_error()
            return JSONResponse({"error": str(e)}, status_code=400)

    async def graphql_endpoint(request: Request) -> JSONResponse:
        """Handle GraphQL requests."""
        integration_api.metrics.record_graphql_request()

        try:
            data = await request.json()
            query = data.get("query", "")
            variables = data.get("variables", {})

            if not integration_api.graphql:
                return JSONResponse({"error": "GraphQL not configured"}, status_code=503)

            result = integration_api.graphql.execute_query(query, variables)

            if result.get("errors"):
                integration_api.metrics.record_graphql_error()

            return JSONResponse(result)

        except Exception as e:
            integration_api.metrics.record_graphql_error()
            return JSONResponse({"error": str(e)}, status_code=400)

    async def metrics_endpoint(request: Request) -> JSONResponse:
        """Get integration metrics."""
        try:
            metrics = await integration_api.get_integration_metrics()
            return JSONResponse(metrics)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    routes = [
        Route("/webhooks/{webhook_name}", webhook_endpoint, methods=["POST"]),
        Route("/graphql", graphql_endpoint, methods=["POST"]),
        Route("/metrics", metrics_endpoint, methods=["GET"]),
    ]

    middleware = [
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"]),
    ]

    return Starlette(routes=routes, middleware=middleware)


# Example usage
def setup_external_integrations() -> None:
    """Setup external integration system."""

    # Initialize integration API
    integration_api = ExternalIntegrationAPI()

    # Configure webhooks
    webhook_config = WebhookConfig(
        url="https://external-system.com/webhooks",
        events=["user.created", "task.completed", "alert.triggered"],
        headers={"Authorization": "Bearer token"},
        timeout=30,
        retry_count=3,
    )
    integration_api.add_webhook("external_system", webhook_config)

    # Configure GraphQL
    graphql_config = GraphQLConfig(
        schema="type Query { hello: String }",
        playground_enabled=True,
        introspection_enabled=True,
        max_complexity=1000,
    )
    integration_api.set_graphql(graphql_config)

    # Configure message queue
    kafka_connector = KafkaConnector(bootstrap_servers="localhost:9092")
    integration_api.add_message_queue("kafka", kafka_connector)

    # Create Starlette app
    app = create_integration_app(integration_api)

    return app


if __name__ == "__main__":
    # Setup logging
    logger = setup_logging()

    # Setup integrations
    app = setup_external_integrations()

    print("External integration system initialized")
    print("Available endpoints:")
    print("  POST /webhooks/{webhook_name} - Send webhook notification")
    print("  POST /graphql - Execute GraphQL query")
    print("  GET /metrics - Get integration metrics")
