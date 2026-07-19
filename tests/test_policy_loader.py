"""Tests for the policy loader."""

import os
import unittest

from aios_core.policy_loader import PolicyLoader


class TestPolicyLoader(unittest.TestCase):
    """PolicyLoader must locate and load the policies directory."""

    def setUp(self):
        self.loader = PolicyLoader()

    def test_policy_dir_resolved(self):
        self.assertTrue(os.path.isdir(self.loader.policy_dir))
        self.assertIn("policies", self.loader.policy_dir.replace("\\", "/"))

    def test_loads_yaml_when_available(self):
        # PyYAML may be absent in minimal envs; loader must not crash.
        if "security_policy" in self.loader.policies:
            sec = self.loader.policies["security_policy"]
            sec = sec.get("security_policy", sec)
            self.assertIn("threat_levels", sec)

    def test_safety_threat_levels_fallback(self):
        # Should not raise regardless of yaml availability.
        levels = self.loader.safety_threat_levels
        self.assertIsInstance(levels, dict)


if __name__ == "__main__":
    unittest.main()
