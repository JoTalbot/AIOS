"""multitenancy smoke test."""
def test_mt(): from aios_core.multitenancy import TenantManager; assert TenantManager().stats() is not None
