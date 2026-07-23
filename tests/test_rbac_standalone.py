"""RBAC standalone test."""
from aios_core.rbac import RBACManager
def test_init(): assert RBACManager() is not None
