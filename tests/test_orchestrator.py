"""Integration test for the full AIOS lifecycle via the Orchestrator."""

import unittest

from aios_core.orchestrator import Orchestrator


class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.orch = Orchestrator()

    def test_valid_action_executes(self):
        trace = self.orch.run({
            "goal": "optimize_task", "scope": "local_module",
            "risk": "low", "reversible": True, "audit_log": True,
        })
        self.assertEqual(trace["verdict"], "ALLOW")
        self.assertEqual(trace["execution"]["status"], "completed")
        self.assertEqual(trace["learned"], "success")

    def test_missing_fields_blocked(self):
        trace = self.orch.run({"goal": "unknown", "scope": "hidden"})
        self.assertEqual(trace["verdict"], "DENY")
        self.assertEqual(trace["execution"]["status"], "blocked")

    def test_global_action_requires_consensus(self):
        trace = self.orch.run({
            "goal": "rewrite_core", "scope": "global",
            "risk": "high", "reversible": False, "audit_log": True,
        })
        self.assertEqual(trace["consensus"], "consensus")
        self.assertEqual(trace["approval"], "pending")

    def test_report_accumulates(self):
        self.orch.run({"goal": "a", "scope": "local_module", "risk": "low",
                       "reversible": True, "audit_log": True})
        report = self.orch.report()
        self.assertEqual(report["decisions"], 1)
        self.assertEqual(report["memories"], 1)


if __name__ == "__main__":
    unittest.main()
