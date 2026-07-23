"""Parametrized deep: benchmark."""
import pytest
from aios_core.benchmark import Benchmark
@pytest.mark.parametrize("n",[1,10,100,500])
def test_bench(n):
    b = Benchmark()
    r = b.run("op",lambda:1,n)
    assert r["iterations"]==n
    assert r["ops_per_second"]>0

