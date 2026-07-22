"""
AIOS External Integration Module

Enhanced external integration capabilities for AIOS including:
- Multiple protocol support (WebSocket, GraphQL, gRPC, SSE, Message Queues)
- Comprehensive monitoring and alerting
- External system connections and data synchronization
- Real-time event streaming
- Performance benchmarking and testing

Main exports:
- create_enhanced_api: Create enhanced AIOS API with integration capabilities
- ExternalIntegrationAPI: Enhanced API with external integration features
- ProtocolManager: Manage multiple communication protocols
- MonitoringSystem: Comprehensive monitoring and alerting
"""

from .app import create_app, AIOSAPI
from .enhanced import create_enhanced_api, EnhancedAIOSAPI
from .integration import ExternalIntegrationAPI, IntegrationEvent, IntegrationEventType
from .protocols import ProtocolManager, ProtocolType, ProtocolConfig
from .monitoring import MonitoringSystem, AlertManager, Alert, AlertSeverity, AlertType

__all__ = [
    'create_app',
    'AIOSAPI',
    'create_enhanced_api',
    'EnhancedAIOSAPI',
    'ExternalIntegrationAPI',
    'IntegrationEvent',
    'IntegrationEventType',
    'ProtocolManager',
    'ProtocolType',
    'ProtocolConfig',
    'MonitoringSystem',
    'AlertManager',
    'Alert',
    'AlertSeverity',
    'AlertType'
]