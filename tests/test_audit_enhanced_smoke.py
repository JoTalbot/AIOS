"""audit_enhanced smoke test."""
def test_ea(): from aios_core.audit_enhanced import EnhancedAudit; assert EnhancedAudit().stats() is not None
