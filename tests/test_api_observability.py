"""Tests for API gateway, audit, and observability modules."""

from aios_core.api_gateway import APIGateway
from aios_core.audit_enhanced import EnhancedAudit
from aios_core.observability import ObservabilityStack
from aios_core.api_versioning import APIVersioning
from aios_core.chaos_testing import ChaosTester


def test_api_gateway_stats():
    s = APIGateway().stats()
    assert isinstance(s, dict)


def test_enhanced_audit_stats():
    s = EnhancedAudit().stats()
    assert isinstance(s, dict)


def test_observability_stack_stats():
    s = ObservabilityStack().stats()
    assert isinstance(s, dict)


def test_api_versioning_stats():
    s = APIVersioning().stats()
    assert isinstance(s, dict)


def test_chaos_tester_stats():
    s = ChaosTester().stats()
    assert isinstance(s, dict)
