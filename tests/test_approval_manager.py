"""Tests for Approval Manager."""

import unittest
from aios_core.approval_manager import ApprovalManager


class TestApprovalManager(unittest.TestCase):
    """Test cases for ApprovalManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = ApprovalManager()

    def test_request_approval(self):
        """Test requesting approval."""
        action = {"name": "test_action", "risk": "high"}
        result = self.manager.request(action)
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["action"], action)

    def test_approve_action(self):
        """Test approving an action."""
        action = {"name": "test_action"}
        self.manager.request(action)
        result = self.manager.approve(0)
        self.assertEqual(result["status"], "approved")

    def test_deny_action(self):
        """Test denying an action."""
        action = {"name": "test_action"}
        self.manager.request(action)
        result = self.manager.deny(0)
        self.assertEqual(result["status"], "denied")


if __name__ == "__main__":
    unittest.main()
