"""Deep benchmark — detailed metrics."""
from aios_core.benchmark import Benchmark
def test_precision():
    b = Benchmark()
    r = b.run("fast", lambda: 42, 10000)
    assert r["iterations"] == 10000
    assert r["ops_per_second"] > 0
    assert r["total_seconds"] > 0
def test_compare_large_difference():
    b = Benchmark()
    b.run("slow", lambda: sum(range(1000)), 10)
    b.run("fast", lambda: 1, 10)
    c = b.compare("fast", "slow")
    assert isinstance(c, str)
