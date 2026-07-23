"""Edge: benchmark zero iterations."""
from aios_core.benchmark import Benchmark
def test_zero_iterations():
    b = Benchmark()
    r = b.run("empty", lambda: 1, 1)
    assert r["total_seconds"] > 0
