"""Tests for API protocols, security, and enhanced modules."""

from aios_core.api.protocols import ProtocolManager as APIProtocolManager
from aios_core.api.security import SecurityMiddleware


def test_api_protocol_manager():
    pm = APIProtocolManager()
    assert pm is not None


def test_security_middleware():
    sm = SecurityMiddleware()
    assert sm is not None
