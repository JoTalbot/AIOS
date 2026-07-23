"""Multitenancy standalone test."""
from aios_core.multitenancy import TenantManager
def test_init(): assert TenantManager() is not None
