"""Benchmark edge."""
from aios_core.benchmark import Benchmark
def test_ops(): b=Benchmark(); r=b.run("fast",lambda:1,10); assert r["ops_per_second"]>0
def test_compare(): b=Benchmark(); b.run("a",lambda:1,10); b.run("b",lambda:1,10); c=b.compare("a","b"); assert isinstance(c,str)
