"""Tests for Approval Manager (legacy compatibility)."""

import unittest

from aios_core.approval_manager import ApprovalManager
from aios_core.storage import Database


class TestApprovalManager(unittest.TestCase):
    """Test cases for ApprovalManager."""

    def setUp(self):
        """Set up test fixtures with in-memory DB."""
        self.db = Database(":memory:")
        self.manager = ApprovalManager(db=self.db)

    def tearDown(self):
        self.db.close()

    def test_request_approval(self):
        """Test requesting approval."""
        action = {"name": "test_action", "risk": "high"}
        result = self.manager.request(action)
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["action"], action)

    def test_approve_action(self):
        """Test approving an action."""
        action = {"name": "test_action"}
        approval = self.manager.request(action)
        result = self.manager.approve(approval["id"])
        self.assertEqual(result["status"], "approved")

    def test_deny_action(self):
        """Test denying an action."""
        action = {"name": "test_action"}
        approval = self.manager.request(action)
        result = self.manager.deny(approval["id"])
        self.assertEqual(result["status"], "denied")


if __name__ == "__main__":
    unittest.main()
