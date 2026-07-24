"""Enhanced Integration System for AIOS - Main Module.

Provides comprehensive external integration capabilities including:
- REST/GraphQL API extensions
- Real-time webhook notifications
- Multiple protocol support (gRPC, AMQP, WebSocket, MQTT)
- Advanced monitoring and observability
- Enhanced logging and analytics
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

from .enhanced_logging import LogConfig, setup_enhanced_logging
from .enhanced_monitoring import (
    AlertRule,
    DashboardConfig,
    MonitoringAPI,
    create_monitoring_app,
)
from .enhanced_protocols import (
    AmqpAdapter,
    GrpcAdapter,
    MqttAdapter,
    ProtocolConfig,
    ProtocolManager,
    ProtocolType,
    WebSocketAdapter,
    create_protocol_app,
)
from .external_integration import (
    ExternalIntegrationAPI,
    GraphQLConfig,
    KafkaConnector,
    WebhookConfig,
    create_integration_app,
)

__all__ = ["EnhancedIntegrationSystem", "IntegrationConfig"]


@dataclass
class IntegrationConfig:
    """Configuration for the enhanced integration system."""

    # External integration settings
    webhook_configs: list[WebhookConfig] = None
    graphql_config: GraphQLConfig = None
    message_queue_configs: dict[str, ProtocolConfig] = None

    # Monitoring settings
    alert_rules: list[AlertRule] = None
    dashboard_configs: list[DashboardConfig] = None

    # Logging settings
    log_config: LogConfig = None

    # Protocol settings
    protocol_configs: dict[str, ProtocolConfig] = None

    def __post_init__(self):
        if self.webhook_configs is None:
            self.webhook_configs = []
        if self.graphql_config is None:
            self.graphql_config = GraphQLConfig(schema="type Query { hello: String }")
        if self.message_queue_configs is None:
            self.message_queue_configs = {}
        if self.alert_rules is None:
            self.alert_rules = []
        if self.dashboard_configs is None:
            self.dashboard_configs = []
        if self.log_config is None:
            self.log_config = LogConfig()
        if self.protocol_configs is None:
            self.protocol_configs = {}


class EnhancedIntegrationSystem:
    """Main integration system that combines all enhanced features."""

    def __init__(self, config: IntegrationConfig):
        """Initialize EnhancedIntegrationSystem."""
        self.config = config
        self.logger = None
        self.integration_api = None
        self.monitoring_api = None
        self.protocol_manager = None
        self.is_running = False

    async def initialize(self) -> None:
        """Initialize the integration system."""
        try:
            # Setup enhanced logging
            self.logger = setup_enhanced_logging(self.config.log_config)

            # Setup external integration API
            self.integration_api = ExternalIntegrationAPI()
            for webhook_config in self.config.webhook_configs:
                self.integration_api.add_webhook(
                    "webhook_" + webhook_config.url, webhook_config
                )

            self.integration_api.set_graphql(self.config.graphql_config)

            # Setup message queue connectors
            for name, queue_config in self.config.message_queue_configs.items():
                if queue_config.protocol_type == ProtocolType.KAFKA:
                    connector = KafkaConnector(queue_config.host)
                    self.integration_api.add_message_queue(name, connector)

            # Setup monitoring API
            self.monitoring_api = MonitoringAPI()
            for alert_rule in self.config.alert_rules:
                self.monitoring_api.add_alert_rule(alert_rule)
            for dashboard_config in self.config.dashboard_configs:
                self.monitoring_api.add_dashboard(dashboard_config)

            # Setup protocol manager
            self.protocol_manager = ProtocolManager()
            for _name, protocol_config in self.config.protocol_configs.items():  # noqa: PERF102
                if protocol_config.protocol_type == ProtocolType.GRPC:
                    adapter = GrpcAdapter(protocol_config)
                elif protocol_config.protocol_type == ProtocolType.AMQP:
                    adapter = AmqpAdapter(protocol_config)
                elif protocol_config.protocol_type == ProtocolType.WEBSOCKET:
                    adapter = WebSocketAdapter(protocol_config)
                elif protocol_config.protocol_type == ProtocolType.MQTT:
                    adapter = MqttAdapter(protocol_config)
                else:
                    continue

                self.protocol_manager.add_adapter(
                    protocol_config.protocol_type, adapter
                )

            self.logger.info("Enhanced integration system initialized successfully")
            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize integration system: {e!s}")
            else:
                print(f"Failed to initialize integration system: {e!s}")
            return False

    async def start(self) -> None:
        """Start the integration system."""
        try:
            if (
                not self.integration_api
                or not self.monitoring_api
                or not self.protocol_manager
            ):
                await self.initialize()

            # Start all adapters
            await self.protocol_manager.start_all()

            self.is_running = True
            self.logger.info("Enhanced integration system started successfully")
            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to start integration system: {e!s}")
            else:
                print(f"Failed to start integration system: {e!s}")
            return False

    async def stop(self) -> None:
        """Stop the integration system."""
        try:
            if self.protocol_manager:
                await self.protocol_manager.stop_all()

            self.is_running = False
            self.logger.info("Enhanced integration system stopped successfully")
            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to stop integration system: {e!s}")
            else:
                print(f"Failed to stop integration system: {e!s}")
            return False

    async def send_webhook(
        self, webhook_name: str, event: str, data: dict[str, Any]
    ) -> bool:
        """Send webhook notification."""
        if not self.integration_api:
            return False
        return await self.integration_api.send_webhook(webhook_name, event, data)

    async def get_system_status(self) -> dict[str, Any]:
        """Get overall system status."""
        status = {
            "is_running": self.is_running,
            "timestamp": time.time(),
            "components": {},
        }

        if self.integration_api:
            status["components"][
                "external_integration"
            ] = await self.integration_api.get_integration_metrics()

        if self.monitoring_api:
            status["components"][
                "monitoring"
            ] = await self.monitoring_api.get_metrics_summary()

        if self.protocol_manager:
            status["components"]["protocols"] = {}
            for protocol_type, adapter in self.protocol_manager.adapters.items():
                status["components"]["protocols"][protocol_type.value] = {
                    "available": True,
                    "connections": len(adapter.active_connections),
                }

        return status

    def create_app(self) -> None:
        """Create Starlette application with all integration endpoints."""
        from starlette.applications import Starlette

        # Create individual apps
        integration_app = create_integration_app(self.integration_api)
        monitoring_app = create_monitoring_app(self.monitoring_api)
        protocol_app = create_protocol_app(self.protocol_manager)

        # Create main app with mounts
        app = Starlette()

        app.mount("/integration", integration_app)
        app.mount("/monitoring", monitoring_app)
        app.mount("/protocols", protocol_app)

        # Add main status endpoint
        @app.route("/status")
        async def status_endpoint(request) -> None:
            """status endpoint."""
            return json.dumps(await self.get_system_status())

        return app


def create_default_config() -> IntegrationConfig:
    """Create default configuration for enhanced integration system."""

    # Default webhook configuration
    webhook_config = WebhookConfig(
        url="https://external-system.com/webhooks",
        events=["user.created", "task.completed", "alert.triggered"],
        headers={"Authorization": "Bearer token"},
        timeout=30,
        retry_count=3,
    )

    # Default GraphQL configuration
    graphql_config = GraphQLConfig(
        schema="""
            type Query {
                hello: String
                systemStatus: String
            }

            type Mutation {
                sendNotification(message: String!): Boolean
            }
        """,
        playground_enabled=True,
        introspection_enabled=True,
        max_complexity=1000,
    )

    # Default alert rules
    alert_rules = [
        AlertRule(
            name="high_cpu_usage",
            metric="cpu_usage",
            condition="value > 80",
            threshold=80,
            duration=300,
            severity="warning",
            notification_channels=["email", "slack"],
        ),
        AlertRule(
            name="high_memory_usage",
            metric="memory_usage",
            condition="value > 90",
            threshold=90,
            duration=300,
            severity="critical",
            notification_channels=["email", "slack", "pagerduty"],
        ),
    ]

    # Default dashboard configuration
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
                "unit": "%",
            },
            {
                "id": "memory_panel",
                "title": "Memory Usage",
                "type": "metric",
                "metric": "memory_usage",
                "unit": "%",
            },
            {
                "id": "response_time_panel",
                "title": "API Response Time",
                "type": "chart",
                "metric": "api_response_time",
                "chart_type": "line",
            },
        ],
    )

    # Default logging configuration
    log_config = LogConfig(
        level="INFO",
        format="json",
        log_file="aios_integration.log",
        max_file_size=10 * 1024 * 1024,
        backup_count=5,
        enable_correlation=True,
        enable_performance_tracking=True,
        ship_to_external=True,
        external_endpoint="https://logs.example.com/api/logs",
    )

    # Default protocol configurations
    protocol_configs = {
        "grpc": ProtocolConfig(
            protocol_type=ProtocolType.GRPC,
            host="localhost",
            port=50051,
            max_connections=100,
        ),
        "amqp": ProtocolConfig(
            protocol_type=ProtocolType.AMQP,
            host="localhost",
            port=5672,
            max_connections=50,
        ),
        "websocket": ProtocolConfig(
            protocol_type=ProtocolType.WEBSOCKET,
            host="localhost",
            port=8001,
            max_connections=200,
        ),
        "mqtt": ProtocolConfig(
            protocol_type=ProtocolType.MQTT,
            host="localhost",
            port=1883,
            max_connections=100,
        ),
    }

    return IntegrationConfig(
        webhook_configs=[webhook_config],
        graphql_config=graphql_config,
        alert_rules=alert_rules,
        dashboard_configs=[dashboard_config],
        log_config=log_config,
        protocol_configs=protocol_configs,
    )


async def main() -> None:
    """Main function to run the enhanced integration system."""
    # Create default configuration
    config = create_default_config()

    # Create and initialize system
    integration_system = EnhancedIntegrationSystem(config)

    # Start the system
    if await integration_system.start():
        print("Enhanced integration system started successfully")

        # Create and run the application
        integration_system.create_app()

        # Print available endpoints
        print("\nAvailable endpoints:")
        print("  GET /status - Get system status")
        print("  POST /integration/webhooks/{webhook_name} - Send webhook notification")
        print("  POST /integration/graphql - Execute GraphQL query")
        print("  GET /integration/metrics - Get integration metrics")
        print("  GET /monitoring/health - Get system health")
        print("  GET /monitoring/alerts - Get alerts")
        print("  GET /monitoring/dashboards/{dashboard_name} - Get dashboard")
        print("  GET /monitoring/metrics - Get monitoring metrics")
        print("  GET /protocols - Get all protocols status")
        print("  WebSocket /monitoring/ws - Real-time monitoring updates")

        # Keep the system running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            await integration_system.stop()
            print("Enhanced integration system stopped")
    else:
        print("Failed to start enhanced integration system")


if __name__ == "__main__":
    asyncio.run(main())
