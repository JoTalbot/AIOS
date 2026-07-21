"""Tests for Constitution Engine."""

import unittest
from aios_core.constitution_engine import ConstitutionEngine


class TestConstitutionEngine(unittest.TestCase):
    """Test cases for ConstitutionEngine."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = ConstitutionEngine()

    def test_valid_action(self):
        """Test evaluation of valid action."""
        action = {
            "goal": "system_health_check",
            "scope": "local_node",
            "risk": "low",
            "audit_log": True,
            "agent_id": "health-check-agent",
            "authority": "reader",
        }
        result = self.engine.evaluate(action)
        self.assertEqual(result["decision"], "ALLOW")

    def test_missing_fields(self):
        """Test evaluation with missing required fields."""
        action = {
            "goal": "test_action"
            # Missing scope, risk, audit_log
        }
        result = self.engine.evaluate(action)
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason"], "missing_required_fields")

    def test_history(self):
        """Test decision history."""
        action = {
            "goal": "test",
            "scope": "local",
            "risk": "low",
            "audit_log": True
        }
        self.engine.evaluate(action)
        self.engine.evaluate(action)
        history = self.engine.history()
        self.assertEqual(len(history), 2)


if __name__ == "__main__":
    unittest.main()
