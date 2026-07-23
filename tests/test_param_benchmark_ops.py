import pytest
from aios_core.benchmark import Benchmark

@pytest.mark.parametrize("n", [10,100,1000,10000])
def test_iterations(n):
    b = Benchmark()
    r = b.run("op", lambda: 1, n)
    assert r["iterations"] == n
    assert r["ops_per_second"] > 0
