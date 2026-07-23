"""
Enhanced Protocol Support for AIOS External Integration

Support for multiple communication protocols: WebSockets, GraphQL, gRPC, SSE, and Message Queues.
Provides protocol adapters and connection management for external systems.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Callable, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import websockets
from graphql import GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString
from graphql import graphql
import grpc
from concurrent import futures

from aios_core.api.integration import (
    ExternalIntegrationManager,
    IntegrationEvent,
    IntegrationEventType,
)
from aios_core.telemetry import MetricCounter, MetricGauge

logger = logging.getLogger(__name__)


class ProtocolType(Enum):
    """Supported communication protocols."""

    WEBSOCKET = "websocket"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    SSE = "sse"
    MESSAGE_QUEUE = "message_queue"
    REST = "rest"


@dataclass
class ProtocolConfig:
    """Configuration for protocol endpoints."""

    protocol_type: ProtocolType
    host: str
    port: int
    endpoint: str
    auth_required: bool = True
    rate_limit: Optional[int] = None
    tls: bool = False
    extra_config: Optional[Dict[str, Any]] = None


class ProtocolAdapter:
    """Base adapter for different communication protocols."""

    def __init__(self, config: ProtocolConfig, integration_manager: ExternalIntegrationManager):
        self.config = config
        self.integration_manager = integration_manager
        self.metrics = {
            "connections": MetricCounter("protocol_connections", "Number of protocol connections"),
            "messages_processed": MetricCounter(
                "protocol_messages", "Number of messages processed"
            ),
            "errors": MetricCounter("protocol_errors", "Number of protocol errors"),
            "active_connections": MetricGauge(
                "protocol_active_connections", "Number of active connections"
            ),
        }

    async def start(self):
        """Start the protocol adapter."""
        raise NotImplementedError

    async def stop(self):
        """Stop the protocol adapter."""
        raise NotImplementedError

    async def handle_message(self, message: Any, connection_id: str = None):
        """Handle incoming message."""
        raise NotImplementedError


class WebSocketAdapter(ProtocolAdapter):
    """WebSocket protocol adapter."""

    def __init__(self, config: ProtocolConfig, integration_manager: ExternalIntegrationManager):
        super().__init__(config, integration_manager)
        self.server = None
        self.clients = {}
        self._running = False

    async def start(self):
        """Start WebSocket server."""
        self._running = True

        async def websocket_handler(websocket, path):
            connection_id = str(uuid.uuid4())
            self.clients[connection_id] = websocket
            self.metrics["connections"].add(1)
            self.metrics["active_connections"].set(len(self.clients))

            try:
                logger.info(f"WebSocket client connected: {connection_id}")

                async for message in websocket:
                    await self.handle_message(message, connection_id)

            except websockets.exceptions.ConnectionClosed:
                logger.info(f"WebSocket client disconnected: {connection_id}")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.metrics["errors"].add(1)
            finally:
                if connection_id in self.clients:
                    del self.clients[connection_id]
                self.metrics["active_connections"].set(len(self.clients))

        self.server = await websockets.serve(
            websocket_handler,
            self.config.host,
            self.config.port,
            ssl=None if not self.config.tls else self._create_ssl_context(),
        )

        logger.info(f"WebSocket server started on {self.config.host}:{self.config.port}")

    async def stop(self):
        """Stop WebSocket server."""
        self._running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        logger.info("WebSocket server stopped")

    async def handle_message(self, message: str, connection_id: str):
        """Handle WebSocket message."""
        try:
            data = json.loads(message)
            event = IntegrationEvent(
                event_type=IntegrationEventType.API_CALL,
                source="websocket",
                timestamp=asyncio.get_event_loop().time(),
                data={
                    "message": data,
                    "connection_id": connection_id,
                    "protocol": "websocket",
                },
            )
            await self.integration_manager.event_queue.put(event)
            self.metrics["messages_processed"].add(1)

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from WebSocket {connection_id}")
            self.metrics["errors"].add(1)
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            self.metrics["errors"].add(1)

    def _create_ssl_context(self):
        """Create SSL context for secure WebSocket."""
        import ssl

        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        # Add certificate configuration here
        return context


class GraphQLAdapter(ProtocolAdapter):
    """GraphQL protocol adapter."""

    def __init__(self, config: ProtocolConfig, integration_manager: ExternalIntegrationManager):
        super().__init__(config, integration_manager)
        self.schema = self._create_schema()

    def _create_schema(self):
        """Create GraphQL schema for AIOS integration."""

        def resolve_integration_events(root, info, **args):
            """Query integration events."""
            return {"events": [], "total": 0}

        def resolve_system_metrics(root, info, **args):
            """Query system metrics."""
            return {"memory_usage": "45%", "cpu_usage": "23%", "active_tasks": 5}

        def trigger_webhook(root, info, **args):
            """Trigger a webhook."""
            endpoint = args.get("endpoint")
            payload = args.get("payload", {})

            if endpoint:
                event = IntegrationEvent(
                    event_type=IntegrationEventType.WEBHOOK,
                    source="graphql",
                    timestamp=asyncio.get_event_loop().time(),
                    data={"endpoint": endpoint, "payload": payload},
                )
                asyncio.create_task(self.integration_manager.event_queue.put(event))
                return {"success": True, "message": f"Webhook {endpoint} triggered"}
            else:
                return {"success": False, "error": "Endpoint required"}

        query_type = GraphQLObjectType(
            name="Query",
            fields={
                "integrationEvents": GraphQLField(
                    GraphQLString,
                    args={"limit": GraphQLString},
                    resolve=resolve_integration_events,
                ),
                "systemMetrics": GraphQLField(GraphQLString, resolve=resolve_system_metrics),
            },
        )

        mutation_type = GraphQLObjectType(
            name="Mutation",
            fields={
                "triggerWebhook": GraphQLField(
                    GraphQLString,
                    args={"endpoint": GraphQLString, "payload": GraphQLString},
                    resolve=trigger_webhook,
                )
            },
        )

        return GraphQLSchema(query=query_type, mutation=mutation_type)

    async def start(self):
        """Start GraphQL server."""
        logger.info(
            f"GraphQL schema created with endpoints on {self.config.host}:{self.config.port}"
        )

    async def stop(self):
        """Stop GraphQL server."""
        logger.info("GraphQL server stopped")

    async def handle_message(self, message: Any, connection_id: str = None):
        """Handle GraphQL query/mutation."""
        try:
            # GraphQL queries are handled via HTTP, but we can process them here
            result = await graphql(self.schema, message)
            self.metrics["messages_processed"].add(1)
            return result
        except Exception as e:
            logger.error(f"GraphQL error: {e}")
            self.metrics["errors"].add(1)
            return {"errors": [str(e)]}


class GrpcAdapter(ProtocolAdapter):
    """gRPC protocol adapter."""

    def __init__(self, config: ProtocolConfig, integration_manager: ExternalIntegrationManager):
        super().__init__(config, integration_manager)
        self.server = None

    async def start(self):
        """Start gRPC server."""

        class IntegrationService(grpc.aio.GenericService):
            async def ProcessEvent(self, request, context):
                """gRPC RPC for processing events."""
                try:
                    event_data = json.loads(request.data)
                    event = IntegrationEvent(
                        event_type=IntegrationEventType.SYSTEM_EVENT,
                        source="grpc",
                        timestamp=asyncio.get_event_loop().time(),
                        data=event_data,
                    )
                    await self.integration_manager.event_queue.put(event)
                    self.metrics["messages_processed"].add(1)

                    return grpc.aio.ProcessEventResponse(
                        success=True, message="Event processed successfully"
                    )
                except Exception as e:
                    logger.error(f"gRPC error: {e}")
                    self.metrics["errors"].add(1)
                    return grpc.aio.ProcessEventResponse(success=False, message=str(e))

        self.server = grpc.aio.server()
        # Add gRPC service here
        # self.server.add_GenericService(IntegrationService())

        listen_addr = f"{self.config.host}:{self.config.port}"
        self.server.add_insecure_port(listen_addr)

        await self.server.start()
        logger.info(f"gRPC server started on {listen_addr}")

    async def stop(self):
        """Stop gRPC server."""
        await self.server.stop(grace=1.0)
        logger.info("gRPC server stopped")


class SSEAdapter(ProtocolAdapter):
    """Server-Sent Events adapter."""

    def __init__(self, config: ProtocolConfig, integration_manager: ExternalIntegrationManager):
        super().__init__(config, integration_manager)
        self.connections = {}
        self._running = False

    async def start(self):
        """Start SSE server."""
        self._running = True
        logger.info(f"SSE server started on {self.config.host}:{self.config.port}")

    async def stop(self):
        """Stop SSE server."""
        self._running = False
        self.connections.clear()
        logger.info("SSE server stopped")

    async def handle_message(self, message: Any, connection_id: str = None):
        """Handle SSE message (typically client subscriptions)."""
        try:
            data = json.loads(message)
            # Handle subscription requests
            if data.get("type") == "subscribe":
                subscription_type = data.get("subscription")
                if connection_id not in self.connections:
                    self.connections[connection_id] = []
                self.connections[connection_id].append(subscription_type)
                self.metrics["messages_processed"].add(1)
        except Exception as e:
            logger.error(f"SSE error: {e}")
            self.metrics["errors"].add(1)

    async def broadcast_event(self, event: IntegrationEvent):
        """Broadcast event to all SSE connections."""
        if not self.connections:
            return

        event_data = {
            "type": "event",
            "data": {
                "event_type": event.event_type.value,
                "source": event.source,
                "timestamp": event.timestamp,
                "data": event.data,
            },
        }

        # Broadcast to all connections
        for connection_id, subscriptions in self.connections.items():
            # Check if connection wants this type of event
            if "*" in subscriptions or event.event_type.value in subscriptions:
                # Send SSE event
                pass  # Implementation depends on HTTP server


class MessageQueueAdapter(ProtocolAdapter):
    """Message Queue adapter (RabbitMQ, Kafka, etc.)."""

    def __init__(self, config: ProtocolConfig, integration_manager: ExternalIntegrationManager):
        super().__init__(config, integration_manager)
        self.queue_config = config.kwargs
        self.consumer = None

    async def start(self):
        """Start message queue consumer."""
        logger.info(f"Message queue adapter started for {self.config.endpoint}")

        # Start consumer based on queue type
        queue_type = self.queue_config.get("type", "memory")

        if queue_type == "memory":
            await self._start_memory_queue()
        elif queue_type == "rabbitmq":
            await self._start_rabbitmq()
        elif queue_type == "kafka":
            await self._start_kafka()
        else:
            logger.warning(f"Unsupported queue type: {queue_type}")

    async def stop(self):
        """Stop message queue consumer."""
        if self.consumer:
            await self.consumer.stop()
        logger.info("Message queue adapter stopped")

    async def _start_memory_queue(self):
        """Start in-memory message queue."""
        # Simple in-memory queue implementation
        pass

    async def _start_rabbitmq(self):
        """Start RabbitMQ consumer."""
        # RabbitMQ integration would go here
        pass

    async def _start_kafka(self):
        """Start Kafka consumer."""
        # Kafka integration would go here
        pass

    async def handle_message(self, message: Any, connection_id: str = None):
        """Handle message from queue."""
        try:
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message

            event = IntegrationEvent(
                event_type=IntegrationEventType.SYSTEM_EVENT,
                source="message_queue",
                timestamp=asyncio.get_event_loop().time(),
                data=data,
            )
            await self.integration_manager.event_queue.put(event)
            self.metrics["messages_processed"].add(1)

        except Exception as e:
            logger.error(f"Message queue error: {e}")
            self.metrics["errors"].add(1)


class ProtocolManager:
    """Manages multiple protocol adapters."""

    def __init__(self, integration_manager: ExternalIntegrationManager):
        self.integration_manager = integration_manager
        self.adapters: Dict[str, ProtocolAdapter] = {}
        self._running = False

    def add_adapter(self, name: str, adapter: ProtocolAdapter):
        """Add a protocol adapter."""
        self.adapters[name] = adapter
        logger.info(f"Added protocol adapter: {name}")

    async def start_all(self):
        """Start all protocol adapters."""
        self._running = True
        for name, adapter in self.adapters.items():
            try:
                await adapter.start()
                logger.info(f"Started protocol adapter: {name}")
            except Exception as e:
                logger.error(f"Failed to start adapter {name}: {e}")

    async def stop_all(self):
        """Stop all protocol adapters."""
        self._running = False
        for name, adapter in self.adapters.items():
            try:
                await adapter.stop()
                logger.info(f"Stopped protocol adapter: {name}")
            except Exception as e:
                logger.error(f"Failed to stop adapter {name}: {e}")

    async def handle_protocol_message(
        self, protocol_name: str, message: Any, connection_id: str = None
    ):
        """Handle message from specific protocol."""
        if protocol_name in self.adapters:
            await self.adapters[protocol_name].handle_message(message, connection_id)
        else:
            logger.error(f"Unknown protocol: {protocol_name}")


def create_protocol_manager(
    integration_manager: ExternalIntegrationManager,
) -> ProtocolManager:
    """Create and configure protocol manager with default adapters."""
    manager = ProtocolManager(integration_manager)

    # Add default adapters
    websocket_config = ProtocolConfig(
        protocol_type=ProtocolType.WEBSOCKET,
        host="localhost",
        port=8765,
        endpoint="/ws",
    )
    manager.add_adapter("websocket", WebSocketAdapter(websocket_config, integration_manager))

    graphql_config = ProtocolConfig(
        protocol_type=ProtocolType.GRAPHQL,
        host="localhost",
        port=8766,
        endpoint="/graphql",
    )
    manager.add_adapter("graphql", GraphQLAdapter(graphql_config, integration_manager))

    sse_config = ProtocolConfig(
        protocol_type=ProtocolType.SSE, host="localhost", port=8767, endpoint="/events"
    )
    manager.add_adapter("sse", SSEAdapter(sse_config, integration_manager))

    return manager
