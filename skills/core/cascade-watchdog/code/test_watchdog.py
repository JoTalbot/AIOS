import unittest
from cascade_watchdog import check_cascade_health

class TestBatch4(unittest.TestCase):
    def test_watchdog_execution(self):
        res = check_cascade_health()
        self.assertIn("Parent Node", res)
        self.assertEqual(res["Parent Node"], "HEALTHY")

if __name__ == "__main__":
    unittest.main()
