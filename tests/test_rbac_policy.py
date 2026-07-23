from aios_core.rbac import RBACManager
def test_policy():
    rm = RBACManager()
    assert rm.stats() is not None