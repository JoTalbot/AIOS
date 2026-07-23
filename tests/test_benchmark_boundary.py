"""benchmark boundary test."""
from aios_core.benchmark import Benchmark

def test_empty_compare(): assert 'Insufficient' in Benchmark().compare('a','b')
