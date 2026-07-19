"""Run the YAML-defined constitution test suite (aios_core/tests/constitution_tests.yaml).

These cases describe expected ALLOW/DENY decisions for the ConstitutionEngine.
Skipped automatically when PyYAML is not installed.
"""

import os
import unittest

from aios_core.constitution_engine import ConstitutionEngine

try:
    import yaml
except ImportError:
    yaml = None


class TestConstitutionYamlSuite(unittest.TestCase):
    """Validate the engine against the declarative test cases."""

    @classmethod
    def setUpClass(cls):
        cls.engine = ConstitutionEngine()
        cls.cases = []
        if yaml is not None:
            path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "aios_core", "tests", "constitution_tests.yaml",
            )
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    data = yaml.safe_load(fh) or {}
                cls.cases = data.get("tests", [])

    def test_suite_loaded(self):
        if yaml is None:
            self.skipTest("PyYAML not installed")
        self.assertTrue(len(self.cases) > 0, "no YAML cases loaded")

    def test_each_case(self):
        if yaml is None:
            self.skipTest("PyYAML not installed")
        for case in self.cases:
            with self.subTest(id=case.get("id")):
                decision = self.engine.evaluate(case["action"])["decision"]
                self.assertEqual(decision, case["expected"])


if __name__ == "__main__":
    unittest.main()
