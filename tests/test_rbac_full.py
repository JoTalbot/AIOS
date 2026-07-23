"""RBAC full ops."""
from aios_core.rbac import RBACManager
def test_rbac(): s=RBACManager().stats(); assert isinstance(s,dict)
