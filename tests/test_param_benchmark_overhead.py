"""Parametrized benchmark overhead tests."""
import pytest
from aios_core.benchmark import Benchmark

@pytest.mark.parametrize("n,expected_min_ops", [(10, 100), (100, 1000), (1000, 10000)])
def test_operations_per_second_scale(n, expected_min_ops):
    b = Benchmark()
    r = b.run("fast", lambda: 1, n)
    assert r["ops_per_second"] > expected_min_ops / 100

@pytest.mark.parametrize("n_benchmarks", [1, 3, 5, 10])
def test_multiple_benchmarks(n_benchmarks):
    b = Benchmark()
    for i in range(n_benchmarks):
        b.run(f"b{i}", lambda: i, 10)
    assert b.stats()["benchmarks"] == n_benchmarks
