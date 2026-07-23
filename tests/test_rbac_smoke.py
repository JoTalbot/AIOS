"""rbac smoke test."""
def test_rbac(): from aios_core.rbac import RBACManager; assert RBACManager().stats() is not None
