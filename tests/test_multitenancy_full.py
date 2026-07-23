"""Multitenancy full."""
from aios_core.multitenancy import TenantManager
def test(): s=TenantManager().stats(); assert isinstance(s,dict)
