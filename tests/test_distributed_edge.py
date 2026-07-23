"""Tests for distributed computing and edge modules."""

from aios_core.distributed_computing import DistributedRuntime
from aios_core.edge_computing import EdgeNode


def test_distributed_runtime_stats():
    dr = DistributedRuntime()
    s = dr.stats()
    assert isinstance(s, dict)


def test_edge_node_stats():
    en = EdgeNode("edge-1")
    s = en.stats()
    assert isinstance(s, dict)
