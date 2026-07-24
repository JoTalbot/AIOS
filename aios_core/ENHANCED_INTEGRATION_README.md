# AIOS Enhanced Integration System

## Overview

The Enhanced Integration System provides comprehensive external integration capabilities for AIOS, including:

- **External API Extensions**: REST/GraphQL API with webhook support
- **Multiple Protocol Support**: gRPC, AMQP, WebSocket 2.0, MQTT
- **Advanced Monitoring**: Real-time dashboards, alerting, and metrics
- **Enhanced Logging**: Structured JSON logging with correlation IDs
- **Production-Ready**: Scalable, secure, and observable

## Features

### 1. External Integration API
- RESTful API endpoints for external integrations
- GraphQL API with schema support
- Webhook notifications with retry logic
- Message queue connectors (Kafka, RabbitMQ)

### 2. Protocol Support
- **gRPC**: High-performance RPC communication
- **AMQP**: Advanced Message Queuing Protocol
- **WebSocket 2.0**: Real-time bidirectional communication
- **MQTT**: IoT device communication

### 3. Enhanced Monitoring
- Real-time dashboards with customizable panels
- Alert rules with severity levels
- Performance metrics and analytics
- WebSocket streaming for live updates

### 4. Enhanced Logging
- Structured JSON logging
- Correlation IDs for tracing
- Performance tracking
- Log aggregation and shipping

## Quick Start

### Basic Usage

```python
import asyncio
from aios_core.enhanced_integration_system import (
    EnhancedIntegrationSystem,
    IntegrationConfig,
)

# Create configuration
config = IntegrationConfig()

# Create and start system
integration_system = EnhancedIntegrationSystem(config)
await integration_system.start()

# Send webhook notification
success = await integration_system.send_webhook(
    "webhook_name", "event_type", {"key": "value"}
)

# Get system status
status = await integration_system.get_system_status()

# Stop the system
await integration_system.stop()
```

### Advanced Configuration

```python
from aios_core.enhanced_integration_system import (
    IntegrationConfig,
    WebhookConfig,
    GraphQLConfig,
    AlertRule,
    DashboardConfig,
    LogConfig,
    ProtocolConfig,
    ProtocolType,
)

# Create advanced configuration
config = IntegrationConfig(
    webhook_configs=[
        WebhookConfig(
            url="https://external-system.com/webhooks",
            events=["user.created", "task.completed"],
            headers={"Authorization": "Bearer token"},
            timeout=30,
            retry_count=3,
        )
    ],
    graphql_config=GraphQLConfig(
        schema="type Query { hello: String }", playground_enabled=True
    ),
    alert_rules=[
        AlertRule(
            name="high_cpu_usage",
            metric="cpu_usage",
            condition="value > 80",
            threshold=80,
            duration=300,
            severity="warning",
            notification_channels=["email", "slack"],
        )
    ],
    dashboard_configs=[
        DashboardConfig(
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
                }
            ],
        )
    ],
    log_config=LogConfig(
        level="INFO",
        format="json",
        log_file="aios.log",
        enable_correlation=True,
        enable_performance_tracking=True,
    ),
    protocol_configs={
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
    },
)
```

## API Endpoints

### Integration Endpoints
- `POST /integration/webhooks/{webhook_name}` - Send webhook notification
- `POST /integration/graphql` - Execute GraphQL query
- `GET /integration/metrics` - Get integration metrics

### Monitoring Endpoints
- `GET /monitoring/health` - Get system health
- `GET /monitoring/alerts` - Get alerts
- `GET /monitoring/dashboards/{dashboard_name}` - Get dashboard
- `GET /monitoring/metrics` - Get monitoring metrics
- `WebSocket /monitoring/ws` - Real-time monitoring updates

### Protocol Endpoints
- `GET /protocols` - Get all protocols status
- `GET /protocols/grpc/status` - Get gRPC status
- `GET /protocols/amqp/status` - Get AMQP status
- `GET /protocols/websocket/status` - Get WebSocket status
- `GET /protocols/mqtt/status` - Get MQTT status

### System Status
- `GET /status` - Get overall system status

## Configuration

### Webhook Configuration

```python
@dataclass
class WebhookConfig:
    url: str  # Webhook URL
    events: List[str]  # List of events to listen for
    headers: Optional[Dict[str, str]]  # Additional headers
    timeout: int = 30  # Request timeout in seconds
    retry_count: int = 3  # Number of retry attempts
```

### GraphQL Configuration

```python
@dataclass
class GraphQLConfig:
    schema: str  # GraphQL schema
    playground_enabled: bool = True
    introspection_enabled: bool = True
    max_complexity: int = 1000  # Maximum query complexity
```

### Alert Rule Configuration

```python
@dataclass
class AlertRule:
    name: str  # Alert rule name
    metric: str  # Metric to monitor
    condition: str  # Condition (e.g., "value > 100")
    threshold: float  # Threshold value
    duration: int  # Duration in seconds
    severity: str  # Severity level
    notification_channels: List[str]  # Notification channels
```

### Dashboard Configuration

```python
@dataclass
class DashboardConfig:
    name: str  # Dashboard name
    title: str  # Dashboard title
    refresh_interval: int  # Refresh interval in seconds
    panels: List[Dict[str, Any]]  # Dashboard panels
```

### Protocol Configuration

```python
@dataclass
class ProtocolConfig:
    protocol_type: ProtocolType  # Protocol type
    host: str  # Host address
    port: int  # Port number
    options: Optional[Dict[str, Any]]  # Additional options
    security: Optional[Dict[str, Any]]  # Security settings
    max_connections: int = 1000  # Maximum connections
    timeout: int = 30  # Timeout in seconds
```

## Examples

### Example 1: Basic Webhook Integration

```python
from aios_core.enhanced_integration_system import (
    EnhancedIntegrationSystem,
    IntegrationConfig,
    WebhookConfig,
)

# Create configuration
config = IntegrationConfig(
    webhook_configs=[
        WebhookConfig(
            url="https://slack.com/webhooks",
            events=["alert.triggered", "task.completed"],
            headers={"Authorization": "Bearer slack-token"},
        )
    ]
)

# Create and start system
integration_system = EnhancedIntegrationSystem(config)
await integration_system.start()

# Send webhook notification
success = await integration_system.send_webhook(
    "webhook_https://slack.com/webhooks",
    "alert.triggered",
    {"alert_id": "alert-123", "severity": "warning"},
)

print(f"Webhook sent: {success}")
```

### Example 2: Monitoring and Alerting

```python
from aios_core.enhanced_integration_system import (
    EnhancedIntegrationSystem,
    IntegrationConfig,
    AlertRule,
    DashboardConfig,
)

# Create configuration with monitoring
config = IntegrationConfig(
    alert_rules=[
        AlertRule(
            name="high_cpu_usage",
            metric="cpu_usage",
            condition="value > 80",
            threshold=80,
            duration=300,
            severity="warning",
            notification_channels=["console"],
        )
    ],
    dashboard_configs=[
        DashboardConfig(
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
                }
            ],
        )
    ],
)

# Create and start system
integration_system = EnhancedIntegrationSystem(config)
await integration_system.start()

# Check system health
health = await integration_system.monitoring_api.get_system_health()
print(f"System health: {health}")
```

### Example 3: Multi-Protocol Support

```python
from aios_core.enhanced_integration_system import (
    EnhancedIntegrationSystem,
    IntegrationConfig,
    ProtocolConfig,
    ProtocolType,
)

# Create configuration with multiple protocols
config = IntegrationConfig(
    protocol_configs={
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
    }
)

# Create and start system
integration_system = EnhancedIntegrationSystem(config)
await integration_system.start()

# Check protocol status
status = await integration_system.get_system_status()
print(f"Protocol status: {status}")
```

## Deployment

### Production Deployment

1. **Environment Configuration**
   ```python
   production_config = IntegrationConfig(
       log_config=LogConfig(
           level="INFO",
           format="json",
           log_file="/var/log/aios/production.log",
           max_file_size=100 * 1024 * 1024,
           backup_count=30,
           ship_to_external=True,
           external_endpoint="https://logs.example.com/api/logs",
       ),
       protocol_configs={
           "grpc": ProtocolConfig(
               protocol_type=ProtocolType.GRPC,
               host="0.0.0.0",
               port=50051,
               security={"tls": True},
           )
       },
   )
   ```

2. **Docker Deployment**
   ```dockerfile
   FROM python:3.9-slim

   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt

   COPY . .

   CMD ["python", "-m", "aios_core.enhanced_integration_system"]
   ```

3. **Kubernetes Deployment**
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: aios-integration
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: aios-integration
     template:
       metadata:
         labels:
           app: aios-integration
       spec:
         containers:
         - name: aios-integration
           image: aios/integration:latest
           ports:
           - containerPort: 8001
           env:
           - name: AIOS_ENVIRONMENT
             value: "production"
   ```

### Scaling Considerations

1. **Horizontal Scaling**
   - Use load balancers for HTTP endpoints
   - Implement connection pooling for databases
   - Use message queues for async processing

2. **Vertical Scaling**
   - Monitor resource usage
   - Optimize database queries
   - Implement caching

3. **Auto-scaling**
   - Use Kubernetes HPA
   - Set up metrics-based scaling
   - Configure scaling policies

## Monitoring and Observability

### Metrics

The system provides various metrics:

- **Integration Metrics**: Webhook success/failure rates, API response times
- **Monitoring Metrics**: Alert counts, system health scores
- **Protocol Metrics**: Connection counts, message throughput
- **Performance Metrics**: Response times, error rates

### Logging

The system uses structured JSON logging with:

- Correlation IDs for tracing
- Performance tracking
- Log aggregation
- External log shipping

### Alerting

The system supports:

- Custom alert rules
- Multiple notification channels
- Alert escalation
- Alert suppression

## Security

### Authentication

- API key authentication
- JWT token support
- OAuth2 integration
- LDAP/Active Directory

### Authorization

- Role-based access control
- Resource-level permissions
- IP whitelisting
- Rate limiting

### Data Protection

- Encryption in transit
- Encryption at rest
- Data masking
- Audit logging

## Troubleshooting

### Common Issues

1. **Webhook Failures**
   - Check network connectivity
   - Verify authentication credentials
   - Monitor webhook response times
   - Review retry configuration

2. **Connection Issues**
   - Check protocol configurations
   - Verify port availability
   - Monitor connection limits
   - Review security settings

3. **Performance Issues**
   - Monitor resource usage
   - Optimize database queries
   - Implement caching
   - Scale horizontally

### Debug Mode

Enable debug logging for troubleshooting:

```python
debug_config = IntegrationConfig(
    log_config=LogConfig(level="DEBUG", format="json", log_file="debug.log")
)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support, please:

1. Check the documentation
2. Search existing issues
3. Create a new issue
4. Contact the development team
