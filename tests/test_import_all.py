"""Smoke test: every aios_core module must import without error."""

import importlib
import pkgutil
import unittest

import aios_core


class TestImportAll(unittest.TestCase):
    """Ensure the whole package is importable as a package."""

    def test_all_modules_importable(self):
        failures = []
        for mod in pkgutil.iter_modules(aios_core.__path__):
            if mod.name == "__init__":
                continue
            try:
                importlib.import_module(f"aios_core.{mod.name}")
            except Exception as exc:  # pragma: no cover - defensive
                failures.append((mod.name, str(exc)))
        self.assertEqual(failures, [], msg="Unimportable modules: %s" % failures)


if __name__ == "__main__":
    unittest.main()
