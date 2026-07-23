"""Performance scenario test."""
from aios_core.benchmark import Benchmark

def test_multi():
    b = Benchmark()
    b.run('a', lambda: sum(range(10)), 100)
    b.run('b', lambda: sum(range(100)), 100)
    assert b.stats()['benchmarks'] == 2
