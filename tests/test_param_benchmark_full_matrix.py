"""Parametrized: benchmark full matrix."""
import pytest
from aios_core.benchmark import Benchmark

@pytest.mark.parametrize("n", [1,10,100,1000,10000])
def test_bench_iterations(n):
    b = Benchmark()
    r = b.run("op", lambda: sum(range(10)), n)
    assert r["iterations"] == n
    assert r["ops_per_second"] > 0

@pytest.mark.parametrize("n_bench", [1,3,5,10])
def test_multi_bench(n_bench):
    b = Benchmark()
    for i in range(n_bench): b.run(f"b{i}", lambda: i, 10)
    assert b.stats()["benchmarks"] == n_bench
