"""Tests for external integration and federation modules."""

from aios_core.external_integration import ExternalIntegrationAPI
from aios_core.federation_manager import FederationManager
from aios_core.multi_agent_orchestrator import MultiAgentOrchestrator


def test_external_integration_stats():
    ei = ExternalIntegrationAPI()
    s = ei.stats()
    assert isinstance(s, dict)


def test_federation_manager_stats():
    fm = FederationManager()
    s = fm.stats()
    assert isinstance(s, dict)


def test_multi_agent_orchestrator_stats():
    mo = MultiAgentOrchestrator()
    s = mo.stats()
    assert isinstance(s, dict)
