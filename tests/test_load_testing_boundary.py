"""load_testing boundary test."""
from aios_core.load_testing import LoadTester

def test_no_calls(): lt = LoadTester(); r = lt.run(lambda: None, 1, 1); assert isinstance(r, dict)
