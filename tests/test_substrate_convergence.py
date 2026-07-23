"""Tests for Universal Substrate-Agnostic Execution Engine (Horizon 8.0)."""

import pytest

from aios_core.substrate_convergence import SubstrateConvergenceEngine, SubstrateType


def test_substrate_selection_and_task_execution():
    engine = SubstrateConvergenceEngine()

    # Default optimal dispatch -> selects Bio-Compute (highest efficiency: 50000 gflops/watt)
    exec_1 = engine.execute_substrate_task({"id": "task_high_speed", "action": "vector_dot"})
    assert exec_1["selected_substrate"] == SubstrateType.BIO_COMPUTE

    # Specific preference request
    exec_2 = engine.execute_substrate_task(
        {"id": "task_quantum", "preferred_type": SubstrateType.QUANTUM}
    )
    assert exec_2["selected_substrate"] == SubstrateType.QUANTUM

    stats = engine.stats()
    assert stats["registered_substrates"] == 5
    assert stats["total_dispatches"] == 2
