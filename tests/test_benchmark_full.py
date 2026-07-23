"""Full tests for benchmarking suite."""

from aios_core.benchmark import Benchmark


def test_benchmark_run():
    b = Benchmark()
    result = b.run("fast_op", lambda: sum(range(10)), iterations=100)
    assert result["iterations"] == 100
    assert result["ops_per_second"] > 0


def test_benchmark_compare():
    b = Benchmark()
    b.run("a", lambda: None, iterations=10)
    b.run("b", lambda: None, iterations=10)
    comparison = b.compare("a", "b")
    assert "faster" in comparison.lower() or "insufficient" in comparison.lower()
