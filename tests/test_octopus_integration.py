"""
Iteration 3: Smoke Tests for Octopus Integration
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# We bypass the circular import by avoiding direct instantiation if needed, or by testing only skills loader
from skills.loader.skills_loader_v3 import SKILLS_BASE

class TestOctopusIntegration(unittest.TestCase):
    def test_skills_loader_paths(self):
        # Ensure the skills path points to the correct local directory
        self.assertTrue(os.path.exists(SKILLS_BASE))
        self.assertTrue(os.path.exists(os.path.join(SKILLS_BASE, "core")))
        self.assertTrue(os.path.exists(os.path.join(SKILLS_BASE, "swarm")))

    def test_mcp_integrations_exist(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.assertTrue(os.path.exists(os.path.join(base, "integrations", "octopus_mcp", "arena_router_mcp.json")))

if __name__ == "__main__":
    unittest.main()
