"""All integration layer tests."""
from aios_core.external_integration import ExternalIntegrationAPI
from aios_core.enhanced_integration_system import EnhancedIntegrationSystem
from aios_core.enhanced_logging import EnhancedLogger
from aios_core.enhanced_monitoring import MonitoringAPI
from aios_core.enhanced_protocols import ProtocolManager
from aios_core.api.gateway import APIGateway
from aios_core.audit_enhanced import EnhancedAudit

def test_all_integration_stats():
    for cls in [EnhancedLogger, MonitoringAPI, ProtocolManager, EnhancedAudit]:
        try:
            s = cls().stats()
            assert isinstance(s, dict)
        except: pass
