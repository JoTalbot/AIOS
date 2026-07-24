"""Enhanced Protocol Support for AIOS.

Provides support for various communication protocols including:
- gRPC for high-performance communication
- AMQP for message queuing
- WebSocket 2.0 for real-time communication
- MQTT for IoT devices
- Custom protocol adapters
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import grpc
from grpc import aio as aio_grpc
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.websockets import WebSocket, WebSocketDisconnect

__all__ = ["ProtocolType", "ProtocolConfig", "ProtocolAdapter", "GrpcAdapter", "AmqpAdapter", "WebSocketAdapter", "MqttAdapter", "ProtocolManager"]


class ProtocolType(Enum):
    """Supported protocol types."""

    GRPC = "grpc"
    AMQP = "amqp"
    WEBSOCKET = "websocket"
    MQTT = "mqtt"
    REST = "rest"
    CUSTOM = "custom"


@dataclass
class ProtocolConfig:
    """Configuration for protocol support."""

    protocol_type: ProtocolType
    host: str
    port: int
    options: dict[str, Any] | None = None
    security: dict[str, Any] | None = None
    max_connections: int = 1000
    timeout: int = 30


class ProtocolAdapter(ABC):
    """Abstract base class for protocol adapters."""

    def __init__(self, config: ProtocolConfig):
        """Initialize ProtocolAdapter."""
        self.config = config
        self.logger = logging.getLogger(f"aios.protocol.{config.protocol_type.value}")
        self.active_connections: list[Any] = []

    @abstractmethod
    async def start(self) -> bool:
        """Start the protocol adapter."""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """Stop the protocol adapter."""
        pass

    @abstractmethod
    async def handle_request(self, request: Any) -> Any:
        """Handle incoming request."""
        pass

    def add_connection(self, connection: Any) -> None:
        """Add active connection."""
        if len(self.active_connections) < self.config.max_connections:
            self.active_connections.append(connection)
            self.logger.info(f"Connection added. Total: {len(self.active_connections)}")
        else:
            self.logger.warning(f"Connection limit reached: {self.config.max_connections}")

    def remove_connection(self, connection: Any) -> None:
        """Remove active connection."""
        if connection in self.active_connections:
            self.active_connections.remove(connection)
            self.logger.info(f"Connection removed. Total: {len(self.active_connections)}")


class GrpcAdapter(ProtocolAdapter):
    """gRPC protocol adapter."""

    def __init__(self, config: ProtocolConfig):
        """Initialize GrpcAdapter."""
        super().__init__(config)
        self.server = None
        self.services: dict[str, Any] = {}

    async def start(self) -> bool:
        """Start gRPC server."""
        try:
            self.server = aio_grpc.server()

            # Add services
            for service_name, service in self.services.items():
                service.add_to_server(self.server)

            # Add port
            listen_addr = f"{self.config.host}:{self.config.port}"
            self.server.add_insecure_port(listen_addr)

            await self.server.start()
            self.logger.info(f"gRPC server started on {listen_addr}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start gRPC server: {str(e)}")
            return False

    async def stop(self) -> bool:
        """Stop gRPC server."""
        try:
            if self.server:
                await self.server.stop(grace=5)
                self.logger.info("gRPC server stopped")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop gRPC server: {str(e)}")
            return False

    async def handle_request(self, request: Any) -> Any:
        """Handle gRPC request."""
        # gRPC requests are handled by the server directly
        pass

    def add_service(self, service_name: str, service: Any) -> None:
        """Add gRPC service."""
        self.services[service_name] = service
        self.logger.info(f"Added gRPC service: {service_name}")


class AmqpAdapter(ProtocolAdapter):
    """AMQP protocol adapter."""

    def __init__(self, config: ProtocolConfig):
        """Initialize AmqpAdapter."""
        super().__init__(config)
        self.connection = None
        self.channel = None
        self.queues: Dict[str, asyncio.Queue] = {}
        self.subscribers: Dict[str, List[Callable]] = {}

    async def start(self) -> bool:
        """Start AMQP connection."""
        try:
            # In production, use aio_pika or similar
            import aio_pika

            connection = await aio_pika.connect_robust(
                host=self.config.host,
                port=self.config.port,
                timeout=self.config.timeout,
            )

            self.connection = connection
            self.channel = await connection.channel()

            # Set QoS
            await self.channel.set_qos(prefetch_count=10)

            self.logger.info(f"AMQP connected to {self.config.host}:{self.config.port}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to AMQP: {str(e)}")
            return False

    async def stop(self) -> bool:
        """Stop AMQP connection."""
        try:
            if self.connection:
                await self.connection.close()
                self.logger.info("AMQP connection closed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to close AMQP connection: {str(e)}")
            return False

    async def handle_request(self, request: Any) -> Any:
        """Handle AMQP request."""
        # AMQP requests are handled by message queues
        pass

    async def publish(self, queue_name: str, message: dict[str, Any]) -> bool:
        """Publish message to queue."""
        try:
            import aio_pika

            if not self.channel:
                return False

            queue = await self.channel.declare_queue(queue_name, durable=True)
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=queue_name,
            )

            self.logger.info(f"Published message to {queue_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to publish message: {str(e)}")
            return False

    async def subscribe(self, queue_name: str, callback: Callable) -> bool:
        """Subscribe to queue."""
        try:
            if queue_name not in self.subscribers:
                self.subscribers[queue_name] = []

            self.subscribers[queue_name].append(callback)

            if not self.channel:
                return False

            queue = await self.channel.declare_queue(queue_name, durable=True)

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    try:
                        data = json.loads(message.body.decode())
                        await callback(data)
                        await message.ack()
                    except Exception as e:
                        self.logger.error(f"Error processing message: {str(e)}")
                        await message.nack()

            return True

        except Exception as e:
            self.logger.error(f"Failed to subscribe to {queue_name}: {str(e)}")
            return False


class WebSocketAdapter(ProtocolAdapter):
    """WebSocket protocol adapter."""

    def __init__(self, config: ProtocolConfig):
        """Initialize WebSocketAdapter."""
        super().__init__(config)
        self.websocket_routes: Dict[str, Callable] = {}

    async def start(self) -> bool:
        """Start WebSocket server."""
        try:
            # WebSocket will be handled by Starlette app
            self.logger.info(f"WebSocket adapter ready for {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket adapter: {str(e)}")
            return False

    async def stop(self) -> bool:
        """Stop WebSocket server."""
        try:
            # Close all connections
            for connection in self.active_connections:
                if hasattr(connection, "close"):
                    await connection.close()
            self.logger.info("WebSocket connections closed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to close WebSocket connections: {str(e)}")
            return False

    async def handle_request(self, websocket: WebSocket) -> Any:
        """Handle WebSocket connection."""
        await websocket.accept()
        self.add_connection(websocket)

        try:
            while True:
                data = await websocket.receive_text()
                await self.handle_message(websocket, data)
        except WebSocketDisconnect:
            self.remove_connection(websocket)

    async def handle_message(self, websocket: WebSocket, message: str) -> None:
        """Handle WebSocket message."""
        try:
            data = json.loads(message)

            # Route message based on type
            msg_type = data.get("type")
            if msg_type in self.websocket_routes:
                response = await self.websocket_routes[msg_type](data)
                await websocket.send_text(json.dumps(response))
            else:
                await websocket.send_text(json.dumps({"error": "Unknown message type"}))

        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {str(e)}")
            await websocket.send_text(json.dumps({"error": str(e)}))

    def add_route(self, msg_type: str, handler: Callable) -> None:
        """Add WebSocket route."""
        self.websocket_routes[msg_type] = handler


class MqttAdapter(ProtocolAdapter):
    """MQTT protocol adapter."""

    def __init__(self, config: ProtocolConfig):
        """Initialize MqttAdapter."""
        super().__init__(config)
        self.client = None
        self.subscriptions: Dict[str, List[Callable]] = {}

    async def start(self) -> bool:
        """Start MQTT client."""
        try:
            # In production, use asyncio-mqtt
            import asyncio_mqtt

            self.client = asyncio_mqtt.Client(
                hostname=self.config.host, port=self.config.port, keepalive=60
            )

            await self.client.__aenter__()
            self.logger.info(f"MQTT connected to {self.config.host}:{self.config.port}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT: {str(e)}")
            return False

    async def stop(self) -> bool:
        """Stop MQTT client."""
        try:
            if self.client:
                await self.client.__aexit__(None, None, None)
                self.logger.info("MQTT client disconnected")
            return True
        except Exception as e:
            self.logger.error(f"Failed to disconnect MQTT client: {str(e)}")
            return False

    async def handle_request(self, request: Any) -> Any:
        """Handle MQTT request."""
        # MQTT requests are handled by subscription callbacks
        pass

    async def publish(self, topic: str, message: dict[str, Any]) -> bool:
        """Publish message to topic."""
        try:
            if not self.client:
                return False

            await self.client.publish(topic, json.dumps(message))
            self.logger.info(f"Published to {topic}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to publish to {topic}: {str(e)}")
            return False

    async def subscribe(self, topic: str, callback: Callable) -> bool:
        """Subscribe to topic."""
        try:
            if topic not in self.subscriptions:
                self.subscriptions[topic] = []

            self.subscriptions[topic].append(callback)

            if not self.client:
                return False

            await self.client.subscribe(topic)

            # Start message handling
            asyncio.create_task(self._handle_messages())

            return True

        except Exception as e:
            self.logger.error(f"Failed to subscribe to {topic}: {str(e)}")
            return False

    async def _handle_messages(self):
        """Handle incoming MQTT messages."""
        try:
            async with self.client.messages() as messages:
                async for message in messages:
                    topic = message.topic
                    payload = json.loads(message.payload.decode())

                    if topic in self.subscriptions:
                        for callback in self.subscriptions[topic]:
                            await callback(payload)

        except Exception as e:
            self.logger.error(f"Error handling MQTT messages: {str(e)}")


class ProtocolManager:
    """Manages multiple protocol adapters."""

    def __init__(self):
        """Initialize ProtocolManager."""
        self.adapters: Dict[ProtocolType, ProtocolAdapter] = {}
        self.logger = logging.getLogger("aios.protocol_manager")

    def add_adapter(self, protocol_type: ProtocolType, adapter: ProtocolAdapter) -> None:
        """Add protocol adapter."""
        self.adapters[protocol_type] = adapter
        self.logger.info(f"Added {protocol_type.value} adapter")

    async def start_all(self) -> bool:
        """Start all adapters."""
        results = {}
        for protocol_type, adapter in self.adapters.items():
            results[protocol_type] = await adapter.start()

        self.logger.info(f"Started adapters: {results}")
        return all(results.values())

    async def stop_all(self) -> bool:
        """Stop all adapters."""
        results = {}
        for protocol_type, adapter in self.adapters.items():
            results[protocol_type] = await adapter.stop()

        self.logger.info(f"Stopped adapters: {results}")
        return all(results.values())

    async def handle_request(self, protocol_type: ProtocolType, request: Any) -> Any:
        """Handle request by protocol type."""
        if protocol_type not in self.adapters:
            raise ValueError(f"Protocol {protocol_type} not supported")

        return await self.adapters[protocol_type].handle_request(request)


def create_protocol_app(protocol_manager: ProtocolManager) -> Starlette:
    """Create Starlette application for protocol support."""

    async def grpc_status_endpoint(request: Request) -> JSONResponse:
        """Get gRPC adapter status."""
        if ProtocolType.GRPC not in protocol_manager.adapters:
            return JSONResponse({"error": "gRPC adapter not available"}, status_code=503)

        adapter = protocol_manager.adapters[ProtocolType.GRPC]
        return JSONResponse(
            {
                "status": "running",
                "connections": len(adapter.active_connections),
                "services": list(adapter.services.keys()),
            }
        )

    async def amqp_status_endpoint(request: Request) -> JSONResponse:
        """Get AMQP adapter status."""
        if ProtocolType.AMQP not in protocol_manager.adapters:
            return JSONResponse({"error": "AMQP adapter not available"}, status_code=503)

        adapter = protocol_manager.adapters[ProtocolType.AMQP]
        return JSONResponse(
            {
                "status": "connected" if adapter.connection else "disconnected",
                "queues": list(adapter.queues.keys()),
                "subscribers": {k: len(v) for k, v in adapter.subscribers.items()},
            }
        )

    async def websocket_status_endpoint(request: Request) -> JSONResponse:
        """Get WebSocket adapter status."""
        if ProtocolType.WEBSOCKET not in protocol_manager.adapters:
            return JSONResponse({"error": "WebSocket adapter not available"}, status_code=503)

        adapter = protocol_manager.adapters[ProtocolType.WEBSOCKET]
        return JSONResponse(
            {
                "status": "running",
                "connections": len(adapter.active_connections),
                "routes": list(adapter.websocket_routes.keys()),
            }
        )

    async def mqtt_status_endpoint(request: Request) -> JSONResponse:
        """Get MQTT adapter status."""
        if ProtocolType.MQTT not in protocol_manager.adapters:
            return JSONResponse({"error": "MQTT adapter not available"}, status_code=503)

        adapter = protocol_manager.adapters[ProtocolType.MQTT]
        return JSONResponse(
            {
                "status": "connected" if adapter.client else "disconnected",
                "subscriptions": {k: len(v) for k, v in adapter.subscriptions.items()},
            }
        )

    async def protocols_endpoint(request: Request) -> JSONResponse:
        """Get all protocols status."""
        status = {}
        for protocol_type in ProtocolType:
            if protocol_type in protocol_manager.adapters:
                adapter = protocol_manager.adapters[protocol_type]
                status[protocol_type.value] = {
                    "available": True,
                    "connections": len(adapter.active_connections),
                }
            else:
                status[protocol_type.value] = {"available": False}

        return JSONResponse(status)

    routes = [
        Route("/protocols", protocols_endpoint),
        Route("/protocols/grpc/status", grpc_status_endpoint),
        Route("/protocols/amqp/status", amqp_status_endpoint),
        Route("/protocols/websocket/status", websocket_status_endpoint),
        Route("/protocols/mqtt/status", mqtt_status_endpoint),
    ]

    middleware = [
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"]),
    ]

    return Starlette(routes=routes, middleware=middleware)


# Example usage
def setup_protocol_support() -> None:
    """Setup protocol support system."""

    # Initialize protocol manager
    protocol_manager = ProtocolManager()

    # Add gRPC adapter
    grpc_config = ProtocolConfig(
        protocol_type=ProtocolType.GRPC,
        host="localhost",
        port=50051,
        max_connections=100,
    )
    grpc_adapter = GrpcAdapter(grpc_config)
    protocol_manager.add_adapter(ProtocolType.GRPC, grpc_adapter)

    # Add AMQP adapter
    amqp_config = ProtocolConfig(
        protocol_type=ProtocolType.AMQP, host="localhost", port=5672, max_connections=50
    )
    amqp_adapter = AmqpAdapter(amqp_config)
    protocol_manager.add_adapter(ProtocolType.AMQP, amqp_adapter)

    # Add WebSocket adapter
    websocket_config = ProtocolConfig(
        protocol_type=ProtocolType.WEBSOCKET,
        host="localhost",
        port=8001,
        max_connections=200,
    )
    websocket_adapter = WebSocketAdapter(websocket_config)
    protocol_manager.add_adapter(ProtocolType.WEBSOCKET, websocket_adapter)

    # Add MQTT adapter
    mqtt_config = ProtocolConfig(
        protocol_type=ProtocolType.MQTT,
        host="localhost",
        port=1883,
        max_connections=100,
    )
    mqtt_adapter = MqttAdapter(mqtt_config)
    protocol_manager.add_adapter(ProtocolType.MQTT, mqtt_adapter)

    # Create Starlette app
    app = create_protocol_app(protocol_manager)

    return app


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Setup protocol support
    app = setup_protocol_support()

    print("Protocol support system initialized")
    print("Available endpoints:")
    print("  GET /protocols - Get all protocols status")
    print("  GET /protocols/grpc/status - Get gRPC status")
    print("  GET /protocols/amqp/status - Get AMQP status")
    print("  GET /protocols/websocket/status - Get WebSocket status")
    print("  GET /protocols/mqtt/status - Get MQTT status")
