"""Tests for Cosmic Scale Swarm Matrix (Horizon 8.0)."""

import pytest
from aios_core.cosmic_swarm_matrix import CosmicSwarmMatrix


def test_cosmic_swarm_matrix_persistence():
    matrix = CosmicSwarmMatrix()

    shard_res = matrix.store_holographic_state(
        shard_key="global_agent_checkpoint_001",
        state_payload={"epoch": 100, "active_agents": 520, "constitutional_hash": "a1b2c3d4"},
    )

    assert shard_res["shard_id"].startswith("holo_")
    assert shard_res["redundancy_count"] == 3
    assert "proxima_centauri_node" in shard_res["replicated_nodes"]

    stats = matrix.stats()
    assert stats["registered_cosmic_nodes"] == 3
    assert stats["holographic_shards_stored"] == 1
