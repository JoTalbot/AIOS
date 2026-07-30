import unittest
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, "/mnt/agents/-Octopus/autopilot")
from server import app

client = TestClient(app)

class TestAutopilotEnhancements(unittest.TestCase):
    def test_health(self):
        res = client.get("/health")
        self.assertEqual(res.status_code, 200)

    def test_otel_traceparent(self):
        res = client.get("/autopilot/tracing/traceparent")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["ok"])
        self.assertTrue(res.json()["traceparent"].startswith("00-"))

    def test_task_reclaim(self):
        res = client.post("/autopilot/tasks/reclaim?max_age_seconds=300")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["ok"])

    def test_memory_sync(self):
        res = client.post("/autopilot/memory/sync")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["ok"])

    def test_leads_summary(self):
        res = client.get("/autopilot/leads/summary")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["ok"])

if __name__ == "__main__":
    unittest.main()
