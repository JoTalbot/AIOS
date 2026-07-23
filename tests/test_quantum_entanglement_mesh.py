"""Tests for Quantum Entangled Zero-Latency Communication Mesh (Horizon 9.0)."""

import pytest

from aios_core.quantum_entanglement_mesh import QuantumEntanglementMesh


def test_quantum_teleportation_sync():
    mesh = QuantumEntanglementMesh()

    sync_res = mesh.sync_instantaneous_state(
        node_a="did:aios:earth_cluster_1",
        node_b="did:aios:alpha_centauri_cluster_9",
        payload={"task_id": "qt_101", "constitutional_state": "valid"},
    )

    assert sync_res["latency_ms"] == 0.0001
    assert sync_res["coherence_fidelity"] == 0.9999
    assert sync_res["teleported_hash"] != ""

    stats = mesh.stats()
    assert stats["active_entangled_channels"] == 1
    assert stats["total_teleportations"] == 1
