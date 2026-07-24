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

# Core API — always available
from .app import AIOSAPI, create_app
from .monitoring import Alert, AlertManager, AlertSeverity, AlertType, MonitoringSystem

# Optional heavy modules — imported lazily via __getattr__
_lazy = {}


def __getattr__(name: str):
    if name in _lazy:
        return _lazy[name]

    if name == "EnhancedAIOSAPI" or name == "create_enhanced_api":
        from .enhanced import EnhancedAIOSAPI as _E
        from .enhanced import create_enhanced_api as _C

        _lazy["EnhancedAIOSAPI"] = _E
        _lazy["create_enhanced_api"] = _C
        return _lazy[name]
    if name in ("ExternalIntegrationAPI", "IntegrationEvent", "IntegrationEventType"):
        from .integration import ExternalIntegrationAPI as _E
        from .integration import IntegrationEvent as _I
        from .integration import IntegrationEventType as _T

        _lazy["ExternalIntegrationAPI"] = _E
        _lazy["IntegrationEvent"] = _I
        _lazy["IntegrationEventType"] = _T
        return _lazy[name]
    if name in ("ProtocolConfig", "ProtocolManager", "ProtocolType"):
        from .protocols import ProtocolConfig as _C
        from .protocols import ProtocolManager as _M
        from .protocols import ProtocolType as _T

        _lazy["ProtocolConfig"] = _C
        _lazy["ProtocolManager"] = _M
        _lazy["ProtocolType"] = _T
        return _lazy[name]
    raise AttributeError(f"module 'aios_core.api' has no attribute {name!r}")


__all__ = [
    "AIOSAPI",
    "Alert",
    "AlertManager",
    "AlertSeverity",
    "AlertType",
    "EnhancedAIOSAPI",
    "ExternalIntegrationAPI",
    "IntegrationEvent",
    "IntegrationEventType",
    "MonitoringSystem",
    "ProtocolConfig",
    "ProtocolManager",
    "ProtocolType",
    "create_app",
    "create_enhanced_api",
]
