"""test_benchmark_scenario test."""
from aios_core.benchmark import Benchmark

def test_relative_performance():
    b = Benchmark()
    b.run("slow", lambda: sum(range(1000)), 10)
    b.run("fast", lambda: sum(range(10)), 10)
    assert b.stats()["benchmarks"] == 2
    assert b.results["fast"]["ops_per_second"] > b.results["slow"]["ops_per_second"]
