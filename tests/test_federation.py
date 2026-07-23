"""Tests for FederationManager v4.0-alpha"""

import pytest

from aios_core.federation_manager import Database, FederationManager, NodeStatus


def test_federation_basic():
    db = Database(":memory:")
    fm = FederationManager(db=db)

    stats = fm.stats()
    assert stats["total_nodes"] >= 1
    assert stats["online_nodes"] >= 1


def test_register_remote_node():
    db = Database(":memory:")
    fm = FederationManager(db=db)

    node = fm.register_node(
        name="remote-node-1", endpoint="http://10.0.0.5:8000", capabilities=["memory", "reasoning"]
    )

    assert node.node_id is not None
    assert node.status == NodeStatus.ONLINE

    retrieved = fm.get_node(node.node_id)
    assert retrieved is not None
    assert retrieved.name == "remote-node-1"


def test_delegate_task():
    db = Database(":memory:")
    fm = FederationManager(db=db)

    remote = fm.register_node("remote", "http://example.com:8000")

    result = fm.delegate_task(remote.node_id, "analyze", {"data": "test"})
    assert result["success"] is True
    assert result["delegated_to"] == remote.node_id


def test_broadcast():
    db = Database(":memory:")
    fm = FederationManager(db=db)

    fm.register_node("node-a", "http://a:8000")
    fm.register_node("node-b", "http://b:8000")

    result = fm.broadcast_message("ping", {"msg": "hello"})
    assert result["success"] is True
    assert result["recipients"] >= 2


def test_heartbeat():
    db = Database(":memory:")
    fm = FederationManager(db=db)

    node = fm.register_node("heartbeat-test", "http://test:8000")
    assert fm.heartbeat(node.node_id) is True
