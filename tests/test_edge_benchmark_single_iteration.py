"""Edge: benchmark with single iteration."""
from aios_core.benchmark import Benchmark

def test_single_iteration():
    b = Benchmark()
    r = b.run("one", lambda: 42, iterations=1)
    assert r["iterations"] == 1
    assert r["ops_per_second"] > 0

def test_compare_same():
    b = Benchmark()
    b.run("a", lambda: 1, 10)
    b.run("b", lambda: 1, 10)
    c = b.compare("a", "b")
    assert isinstance(c, str)
