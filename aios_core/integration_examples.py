"""Enhanced Integration System - Usage Examples and Integration Guide.

This module provides examples and documentation for using the enhanced integration system.
"""

import asyncio
import json
import time
from typing import Any, Dict, List
from dataclasses import asdict

from .enhanced_integration_system import (
    EnhancedIntegrationSystem,
    IntegrationConfig,
    WebhookConfig,
    GraphQLConfig,
    AlertRule,
    DashboardConfig,
    LogConfig,
    ProtocolConfig,
    ProtocolType,
)


async def example_basic_usage():
    """Example of basic usage of the enhanced integration system."""

    print("=== Enhanced Integration System - Basic Usage Example ===")

    # Create configuration
    config = IntegrationConfig(
        webhook_configs=[
            WebhookConfig(
                url="https://httpbin.org/post",
                events=["user.created", "task.completed"],
                headers={"Content-Type": "application/json"},
                timeout=10,
                retry_count=2,
            )
        ],
        alert_rules=[
            AlertRule(
                name="example_alert",
                metric="example_metric",
                condition="value > 50",
                threshold=50,
                duration=60,
                severity="warning",
                notification_channels=["console"],
            )
        ],
        dashboard_configs=[
            DashboardConfig(
                name="example_dashboard",
                title="Example Dashboard",
                refresh_interval=30,
                panels=[
                    {
                        "id": "metric_panel",
                        "title": "Example Metric",
                        "type": "metric",
                        "metric": "example_metric",
                        "unit": "count",
                    }
                ],
            )
        ],
    )

    # Create integration system
    integration_system = EnhancedIntegrationSystem(config)

    # Start the system
    if await integration_system.start():
        print("Integration system started successfully")

        # Send webhook notification
        success = await integration_system.send_webhook(
            "webhook_https://httpbin.org/post",
            "user.created",
            {"user_id": "123", "name": "John Doe"},
        )
        print(f"Webhook sent: {success}")

        # Get system status
        status = await integration_system.get_system_status()
        print(f"System status: {json.dumps(status, indent=2)}")

        # Stop the system
        await integration_system.stop()
        print("Integration system stopped")


async def example_advanced_usage():
    """Example of advanced usage with multiple protocols and monitoring."""

    print("\n=== Enhanced Integration System - Advanced Usage Example ===")

    # Create advanced configuration
    config = IntegrationConfig(
        webhook_configs=[
            WebhookConfig(
                url="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
                events=["alert.triggered", "system.error"],
                headers={"Authorization": "Bearer slack-token"},
                timeout=30,
                retry_count=3,
            ),
            WebhookConfig(
                url="https://api.example.com/webhooks",
                events=["data.ingested", "model.deployed"],
                headers={"X-API-Key": "api-key"},
                timeout=15,
                retry_count=2,
            ),
        ],
        graphql_config=GraphQLConfig(
            schema="""
                type Query {
                    systemHealth: SystemHealth
                    activeAlerts: [Alert!]
                    integrationMetrics: IntegrationMetrics
                }

                type Mutation {
                    sendWebhook(event: String!, data: JSON!): Boolean
                    createAlert(name: String!, metric: String!, threshold: Float!): Boolean
                }

                type SystemHealth {
                    status: String
                    score: Float
                    timestamp: String
                }

                type Alert {
                    name: String
                    severity: String
                    triggered: Boolean
                    timestamp: String
                }

                type IntegrationMetrics {
                    webhooks: WebhookMetrics
                    monitoring: MonitoringMetrics
                    protocols: ProtocolMetrics
                }

                type WebhookMetrics {
                    sent: Int
                    failed: Int
                    successRate: Float
                }

                type MonitoringMetrics {
                    alerts: Int
                    systemHealth: Float
                    responseTime: Float
                }

                type ProtocolMetrics {
                    grpc: ProtocolStatus
                    amqp: ProtocolStatus
                    websocket: ProtocolStatus
                    mqtt: ProtocolStatus
                }

                type ProtocolStatus {
                    available: Boolean
                    connections: Int
                }

                scalar JSON
            """,
            playground_enabled=True,
            introspection_enabled=True,
            max_complexity=2000,
        ),
        alert_rules=[
            AlertRule(
                name="high_response_time",
                metric="response_time",
                condition="value > 1000",
                threshold=1000,
                duration=300,
                severity="warning",
                notification_channels=["slack", "email"],
            ),
            AlertRule(
                name="error_rate_high",
                metric="error_rate",
                condition="value > 0.05",
                threshold=0.05,
                duration=600,
                severity="critical",
                notification_channels=["slack", "email", "pagerduty"],
            ),
            AlertRule(
                name="memory_usage_high",
                metric="memory_usage",
                condition="value > 85",
                threshold=85,
                duration=180,
                severity="warning",
                notification_channels=["console"],
            ),
        ],
        dashboard_configs=[
            DashboardConfig(
                name="system_overview",
                title="System Overview",
                refresh_interval=30,
                panels=[
                    {
                        "id": "health_panel",
                        "title": "System Health",
                        "type": "metric",
                        "metric": "system_health",
                        "unit": "%",
                    },
                    {
                        "id": "response_time_panel",
                        "title": "Response Time",
                        "type": "chart",
                        "metric": "response_time",
                        "chart_type": "line",
                    },
                    {
                        "id": "error_rate_panel",
                        "title": "Error Rate",
                        "type": "metric",
                        "metric": "error_rate",
                        "unit": "%",
                    },
                    {
                        "id": "memory_panel",
                        "title": "Memory Usage",
                        "type": "metric",
                        "metric": "memory_usage",
                        "unit": "%",
                    },
                ],
            ),
            DashboardConfig(
                name="webhook_dashboard",
                title="Webhook Activity",
                refresh_interval=60,
                panels=[
                    {
                        "id": "webhook_sent_panel",
                        "title": "Webhooks Sent",
                        "type": "metric",
                        "metric": "webhooks_sent",
                        "unit": "count",
                    },
                    {
                        "id": "webhook_failed_panel",
                        "title": "Webhooks Failed",
                        "type": "metric",
                        "metric": "webhooks_failed",
                        "unit": "count",
                    },
                    {
                        "id": "webhook_success_rate_panel",
                        "title": "Success Rate",
                        "type": "metric",
                        "metric": "webhook_success_rate",
                        "unit": "%",
                    },
                ],
            ),
        ],
        log_config=LogConfig(
            level="INFO",
            format="json",
            log_file="aios_advanced_integration.log",
            max_file_size=50 * 1024 * 1024,  # 50MB
            backup_count=10,
            enable_correlation=True,
            enable_performance_tracking=True,
            ship_to_external=True,
            external_endpoint="https://logs.example.com/api/logs",
        ),
        protocol_configs={
            "grpc": ProtocolConfig(
                protocol_type=ProtocolType.GRPC,
                host="localhost",
                port=50051,
                max_connections=100,
                options={"grpc.max_send_message_length": 4 * 1024 * 1024},
            ),
            "amqp": ProtocolConfig(
                protocol_type=ProtocolType.AMQP,
                host="localhost",
                port=5672,
                max_connections=50,
                security={"username": "guest", "password": "guest"},
            ),
            "websocket": ProtocolConfig(
                protocol_type=ProtocolType.WEBSOCKET,
                host="localhost",
                port=8001,
                max_connections=200,
                security={"origin": ["http://localhost:3000"]},
            ),
            "mqtt": ProtocolConfig(
                protocol_type=ProtocolType.MQTT,
                host="localhost",
                port=1883,
                max_connections=100,
                security={"username": "mqtt", "password": "password"},
            ),
        },
    )

    # Create integration system
    integration_system = EnhancedIntegrationSystem(config)

    # Start the system
    if await integration_system.start():
        print("Advanced integration system started successfully")

        # Send multiple webhook notifications
        events = [
            ("alert.triggered", {"alert_id": "alert-123", "severity": "warning"}),
            ("data.ingested", {"dataset": "users", "records": 1000}),
            ("model.deployed", {"model": "v1.0", "accuracy": 0.95}),
        ]

        for event, data in events:
            success = await integration_system.send_webhook(
                "webhook_https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
                event,
                data,
            )
            print(f"Webhook sent for {event}: {success}")

        # Simulate some metrics
        await simulate_system_metrics(integration_system)

        # Get detailed system status
        status = await integration_system.get_system_status()
        print(f"System status: {json.dumps(status, indent=2)}")

        # Stop the system
        await integration_system.stop()
        print("Advanced integration system stopped")


async def simulate_system_metrics(integration_system: EnhancedIntegrationSystem):
    """Simulate system metrics for demonstration."""

    print("Simulating system metrics...")

    # Simulate various metrics over time
    for i in range(10):
        # Simulate response time
        response_time = 500 + (i * 100)  # Increasing response time
        if response_time > 1000:
            # Trigger alert
            await integration_system.monitoring_api.alert_manager.check_metric(
                "response_time", response_time, time.time()
            )

        # Simulate error rate
        error_rate = 0.01 + (i * 0.005)  # Increasing error rate
        if error_rate > 0.05:
            # Trigger alert
            await integration_system.monitoring_api.alert_manager.check_metric(
                "error_rate", error_rate, time.time()
            )

        # Simulate memory usage
        memory_usage = 60 + (i * 5)  # Increasing memory usage
        if memory_usage > 85:
            # Trigger alert
            await integration_system.monitoring_api.alert_manager.check_metric(
                "memory_usage", memory_usage, time.time()
            )

        # Update system health
        health_score = 100 - (i * 5)
        integration_system.monitoring_api.metrics.set_system_health(health_score)

        await asyncio.sleep(1)


async def example_integration_with_aios_core():
    """Example of integrating with AIOS core components."""

    print("\n=== Integration with AIOS Core Components Example ===")

    # This example shows how to integrate the enhanced integration system
    # with existing AIOS core components

    from .external_integration import ExternalIntegrationAPI
    from .enhanced_monitoring import MonitoringAPI
    from .enhanced_logging import EnhancedLogger

    # Create individual components
    integration_api = ExternalIntegrationAPI()
    monitoring_api = MonitoringAPI()
    logger = EnhancedLogger(LogConfig())

    # Configure integration API
    webhook_config = WebhookConfig(
        url="https://external-system.com/webhooks",
        events=["task.completed", "user.created"],
        headers={"Authorization": "Bearer token"},
    )
    integration_api.add_webhook("external_system", webhook_config)

    # Configure monitoring API
    alert_rule = AlertRule(
        name="aios_performance",
        metric="aios_response_time",
        condition="value > 500",
        threshold=500,
        duration=300,
        severity="warning",
        notification_channels=["console"],
    )
    monitoring_api.add_alert_rule(alert_rule)

    # Set up logging
    logger.set_correlation_id("correlation-12345")
    logger.set_trace_context("trace-123", "span-456")

    # Log integration events
    logger.info(
        "AIOS integration system initialized",
        components=["external_api", "monitoring", "logging"],
    )

    # Simulate AIOS core events
    aios_events = [
        {"type": "task.completed", "task_id": "task-123", "status": "success"},
        {"type": "user.created", "user_id": "user-456", "email": "user@example.com"},
        {"type": "system.alert", "alert_id": "alert-789", "severity": "warning"},
    ]

    for event in aios_events:
        # Send webhook notification
        success = await integration_api.send_webhook("external_system", event["type"], event)
        logger.info(f"Webhook sent for {event['type']}", success=success)

        # Check monitoring alerts
        if event["type"] == "system.alert":
            await monitoring_api.alert_manager.check_metric("aios_alerts", 1, time.time())

        # Log the event
        logger.info(f"AIOS event processed", event_type=event["type"])

    # Get monitoring metrics
    metrics = await monitoring_api.get_metrics_summary()
    logger.info("Monitoring metrics retrieved", metrics=metrics)

    print("AIOS core integration example completed")


async def example_deployment_configuration():
    """Example of deployment configuration for the enhanced integration system."""

    print("\n=== Deployment Configuration Example ===")

    # Production configuration
    production_config = IntegrationConfig(
        webhook_configs=[
            WebhookConfig(
                url="https://production-webhooks.example.com",
                events=["critical.alert", "deployment.completed"],
                headers={
                    "Authorization": "Bearer prod-token",
                    "X-Environment": "production",
                },
                timeout=60,
                retry_count=5,
            )
        ],
        alert_rules=[
            AlertRule(
                name="production_error_rate",
                metric="error_rate",
                condition="value > 0.01",
                threshold=0.01,
                duration=300,
                severity="critical",
                notification_channels=["pagerduty", "slack"],
            ),
            AlertRule(
                name="production_latency",
                metric="response_time",
                condition="value > 2000",
                threshold=2000,
                duration=600,
                severity="warning",
                notification_channels=["slack"],
            ),
        ],
        log_config=LogConfig(
            level="INFO",
            format="json",
            log_file="/var/log/aios/production.log",
            max_file_size=100 * 1024 * 1024,  # 100MB
            backup_count=30,
            enable_correlation=True,
            enable_performance_tracking=True,
            ship_to_external=True,
            external_endpoint="https://logs.example.com/api/logs",
        ),
        protocol_configs={
            "grpc": ProtocolConfig(
                protocol_type=ProtocolType.GRPC,
                host="0.0.0.0",
                port=50051,
                max_connections=1000,
                security={"tls": True, "cert_file": "/etc/aios/grpc.crt"},
            ),
            "amqp": ProtocolConfig(
                protocol_type=ProtocolType.AMQP,
                host="amqp.example.com",
                port=5672,
                max_connections=500,
                security={
                    "username": "prod_user",
                    "password": "prod_password",
                    "ssl": True,
                },
            ),
            "websocket": ProtocolConfig(
                protocol_type=ProtocolType.WEBSOCKET,
                host="0.0.0.0",
                port=8001,
                max_connections=2000,
                security={"origin": ["https://app.example.com"], "auth": True},
            ),
        },
    )

    # Development configuration
    development_config = IntegrationConfig(
        webhook_configs=[
            WebhookConfig(
                url="https://webhooks.example.com/dev",
                events=["*.alert", "*.completed"],
                headers={"Authorization": "Bearer dev-token"},
                timeout=30,
                retry_count=2,
            )
        ],
        alert_rules=[
            AlertRule(
                name="dev_error_rate",
                metric="error_rate",
                condition="value > 0.1",
                threshold=0.1,
                duration=120,
                severity="warning",
                notification_channels=["console"],
            )
        ],
        log_config=LogConfig(
            level="DEBUG",
            format="json",
            log_file="dev.log",
            max_file_size=10 * 1024 * 1024,  # 10MB
            backup_count=5,
            enable_correlation=True,
            enable_performance_tracking=False,
            ship_to_external=False,
        ),
        protocol_configs={
            "grpc": ProtocolConfig(
                protocol_type=ProtocolType.GRPC,
                host="localhost",
                port=50051,
                max_connections=100,
                security={"tls": False},
            ),
            "amqp": ProtocolConfig(
                protocol_type=ProtocolType.AMQP,
                host="localhost",
                port=5672,
                max_connections=50,
                security={"username": "guest", "password": "guest"},
            ),
            "websocket": ProtocolConfig(
                protocol_type=ProtocolType.WEBSOCKET,
                host="localhost",
                port=8001,
                max_connections=100,
                security={"auth": False},
            ),
        },
    )

    print("Production configuration:")
    print(json.dumps(asdict(production_config), indent=2))

    print("\nDevelopment configuration:")
    print(json.dumps(asdict(development_config), indent=2))

    print("\nDeployment configuration example completed")


async def main():
    """Run all examples."""
    print("Enhanced Integration System - Examples and Guide")
    print("=" * 50)

    # Run basic usage example
    await example_basic_usage()

    # Run advanced usage example
    await example_advanced_usage()

    # Run AIOS core integration example
    await example_integration_with_aios_core()

    # Run deployment configuration example
    await example_deployment_configuration()

    print("\nAll examples completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
