"""
Enhanced AIOS API Integration Example

Demonstrates how to use the enhanced AIOS API with external integration capabilities.
Shows setup, configuration, and usage examples.
"""

import asyncio
import logging
import time

from aios_core.api.enhanced import create_enhanced_api
from aios_core.api.integration import IntegrationEvent, IntegrationEventType

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main example demonstrating enhanced AIOS API usage."""

    # Create enhanced API
    api = create_enhanced_api(db_path=":memory:")

    # Start background services
    await api.start_background_services()

    try:
        # Create enhanced app
        api.create_enhanced_app()

        logger.info("Enhanced AIOS API created and started")

        # Example 1: Create a webhook integration
        await create_webhook_integration(api)

        # Example 2: Configure protocols
        await configure_protocols(api)

        # Example 3: Create monitoring alerts
        await create_monitoring_alerts(api)

        # Example 4: Test external system connections
        await test_external_connections(api)

        # Example 5: Run data synchronization
        await run_data_sync(api)

        # Example 6: Integration benchmarking
        await run_benchmark(api)

        # Keep the server running
        logger.info("Examples completed. Server is running...")

        # Simulate some activity
        await simulate_activity(api)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Stop background services
        await api.stop_background_services()
        logger.info("Background services stopped")


async def create_webhook_integration(api) -> None:
    """Example: Create a webhook integration."""
    logger.info("Creating webhook integration...")

    # Create webhook integration
    webhook_data = {
        "type": "webhook",
        "config": {
            "endpoint": "/orders/webhook",
            "handler_url": "https://example.com/webhook-handler",
        },
    }

    response = await api.integration_api._integrations_create(
        type(webhook_data).__dict__, webhook_data
    )
    logger.info(f"Webhook integration created: {response}")


async def configure_protocols(api) -> None:
    """Example: Configure communication protocols."""
    logger.info("Configuring protocols...")

    # Configure WebSocket protocol
    websocket_config = {
        "type": "websocket",
        "config": {
            "host": "localhost",
            "port": 8765,
            "endpoint": "/ws",
            "auth_required": True,
        },
    }

    response = await api._protocols_configure(
        type(websocket_config).__dict__, websocket_config
    )
    logger.info(f"WebSocket protocol configured: {response}")

    # Configure GraphQL protocol
    graphql_config = {
        "type": "graphql",
        "config": {"host": "localhost", "port": 8766, "endpoint": "/graphql"},
    }

    response = await api._protocols_configure(
        type(graphql_config).__dict__, graphql_config
    )
    logger.info(f"GraphQL protocol configured: {response}")


async def create_monitoring_alerts(api) -> None:
    """Example: Create monitoring alerts."""
    logger.info("Creating monitoring alerts...")

    # Create performance alert
    performance_alert = {
        "type": "performance",
        "severity": "high",
        "title": "High CPU Usage",
        "message": "CPU usage is above 80%",
        "metadata": {"cpu_threshold": 80.0},
    }

    response = await api._monitoring_alerts_create(
        type(performance_alert).__dict__, performance_alert
    )
    logger.info(f"Performance alert created: {response}")

    # Create error rate alert
    error_alert = {
        "type": "error_rate",
        "severity": "medium",
        "title": "High Error Rate",
        "message": "Error rate is above 5%",
        "metadata": {"error_threshold": 0.05},
    }

    response = await api._monitoring_alerts_create(
        type(error_alert).__dict__, error_alert
    )
    logger.info(f"Error rate alert created: {response}")


async def test_external_connections(api) -> None:
    """Example: Test external system connections."""
    logger.info("Testing external connections...")

    # Connect to external API
    external_system = {
        "id": "external_api_1",
        "config": {
            "base_url": "https://api.example.com",
            "api_key": "your-api-key",
            "timeout": 30,
        },
    }

    response = await api._external_systems_connect(
        type(external_system).__dict__, external_system
    )
    logger.info(f"External system connected: {response}")

    # Get system status
    response = await api._external_systems_status("external_api_1")
    logger.info(f"External system status: {response}")


async def run_data_sync(api) -> None:
    """Example: Run data synchronization."""
    logger.info("Running data synchronization...")

    # Sync data from external system
    sync_data = {
        "source": "external_api_1",
        "target": "local_database",
        "sync_type": "full_sync",
    }

    response = await api._sync_external(type(sync_data).__dict__, sync_data)
    logger.info(f"Data sync initiated: {response}")

    # Check sync status
    response = await api._sync_status()
    logger.info(f"Sync status: {response}")


async def run_benchmark(api) -> None:
    """Example: Run integration benchmark."""
    logger.info("Running integration benchmark...")

    # Run webhook benchmark
    benchmark_data = {"type": "webhook", "duration": 30, "rate": 20}

    response = await api._integration_benchmark(
        type(benchmark_data).__dict__, benchmark_data
    )
    logger.info(f"Benchmark results: {response}")


async def simulate_activity(api) -> None:
    """Simulate system activity for demonstration."""
    logger.info("Simulating system activity...")

    # Simulate API requests
    for i in range(10):
        await asyncio.sleep(1)

        # Simulate webhook event
        webhook_event = IntegrationEvent(
            event_type=IntegrationEventType.WEBHOOK,
            source="test",
            timestamp=time.time(),
            data={
                "endpoint": f"/test/webhook_{i}",
                "payload": {"test_id": i, "timestamp": time.time()},
            },
        )

        await api.integration_api.integration_manager.event_queue.put(webhook_event)

        # Simulate integration event
        integration_event = IntegrationEvent(
            event_type=IntegrationEventType.SYSTEM_EVENT,
            source="test_system",
            timestamp=time.time(),
            data={"event_id": i, "message": f"Test event {i}"},
        )

        await api.integration_api.integration_manager.event_queue.put(integration_event)

        logger.info(f"Simulated activity {i}/10")

    logger.info("Activity simulation completed")


# Example usage functions for different scenarios


async def setup_production_environment() -> None:
    """Setup production environment with enhanced API."""
    logger.info("Setting up production environment...")

    # Create API with production settings
    api = create_enhanced_api(
        db_path="/data/aios.db",
        auth_required=True,
        api_keys={"prod-key": {"subject": "system", "roles": ["admin"]}},
    )

    # Configure production protocols
    await configure_production_protocols(api)

    # Setup production monitoring
    await setup_production_monitoring(api)

    return api


async def configure_production_protocols(api) -> None:
    """Configure protocols for production."""
    logger.info("Configuring production protocols...")

    # Configure secure WebSocket
    websocket_config = {
        "type": "websocket",
        "config": {
            "host": "0.0.0.0",
            "port": 8765,
            "endpoint": "/ws",
            "auth_required": True,
            "tls": True,
            "rate_limit": 100,
        },
    }

    await api._protocols_configure(type(websocket_config).__dict__, websocket_config)

    # Configure GraphQL with SSL
    graphql_config = {
        "type": "graphql",
        "config": {
            "host": "0.0.0.0",
            "port": 8766,
            "endpoint": "/graphql",
            "tls": True,
        },
    }

    await api._protocols_configure(type(graphql_config).__dict__, graphql_config)


async def setup_production_monitoring(api) -> None:
    """Setup production monitoring."""
    logger.info("Setting up production monitoring...")

    # Create critical alerts
    critical_alert = {
        "type": "critical",
        "severity": "critical",
        "title": "System Critical Error",
        "message": "Critical system error detected",
        "metadata": {"escalation": "immediate"},
    }

    await api._monitoring_alerts_create(type(critical_alert).__dict__, critical_alert)

    # Setup performance monitoring
    performance_alert = {
        "type": "performance",
        "severity": "high",
        "title": "Performance Degradation",
        "message": "System performance is degraded",
        "metadata": {"threshold": 0.8},
    }

    await api._monitoring_alerts_create(
        type(performance_alert).__dict__, performance_alert
    )


async def demonstrate_error_handling() -> None:
    """Demonstrate error handling in integrations."""
    logger.info("Demonstrating error handling...")

    api = create_enhanced_api()

    try:
        # Test invalid webhook configuration
        invalid_config = {
            "type": "webhook",
            "config": {
                "endpoint": "",  # Missing endpoint
                "handler_url": "https://example.com/handler",
            },
        }

        response = await api._integrations_create(
            type(invalid_config).__dict__, invalid_config
        )
        logger.warning(f"Expected error for invalid config: {response}")

        # Test invalid protocol configuration
        invalid_protocol = {"type": "invalid_protocol", "config": {}}

        response = await api._protocols_configure(
            type(invalid_protocol).__dict__, invalid_protocol
        )
        logger.warning(f"Expected error for invalid protocol: {response}")

    except Exception as e:
        logger.error(f"Error handling demonstration failed: {e}")


if __name__ == "__main__":
    # Run main example
    asyncio.run(main())

    # Or run specific examples
    # asyncio.run(setup_production_environment())
    # asyncio.run(demonstrate_error_handling())
