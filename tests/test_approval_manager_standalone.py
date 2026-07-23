"""approval_manager standalone test."""
from aios_core.approval_manager import ApprovalManager
def test_init(): s = ApprovalManager().stats(); assert isinstance(s, dict)
