"""External integration ops."""
from aios_core.external_integration import ExternalIntegrationAPI
def test_ei(): assert ExternalIntegrationAPI() is not None
