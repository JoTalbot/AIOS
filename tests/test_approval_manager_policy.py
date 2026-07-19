"""Tests for policy-driven approval behaviour."""

import unittest

from aios_core.approval_manager import ApprovalManager


class TestApprovalPolicy(unittest.TestCase):
    def setUp(self):
        self.mgr = ApprovalManager()

    def test_low_risk_auto_approved(self):
        res = self.mgr.request({"scope": "local_module", "risk": "low"})
        self.assertEqual(res["status"], "auto_approved")

    def test_high_risk_pending(self):
        res = self.mgr.request({"scope": "local_module", "risk": "high"})
        self.assertEqual(res["status"], "pending")

    def test_global_scope_pending(self):
        res = self.mgr.request({"scope": "global", "risk": "low"})
        self.assertEqual(res["status"], "pending")

    def test_approve_and_deny(self):
        self.mgr.request({"scope": "local_module", "risk": "low"})
        self.assertEqual(self.mgr.approve(0)["status"], "approved")
        self.mgr.request({"scope": "local_module", "risk": "low"})
        self.assertEqual(self.mgr.deny(1)["status"], "denied")


if __name__ == "__main__":
    unittest.main()
