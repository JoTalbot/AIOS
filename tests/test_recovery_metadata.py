from execution.recovery import RecoveryAction, RecoveryEngine, RecoverySignal


def test_checkpoint_metadata_survives_recovery_decision():
    engine = RecoveryEngine(max_retries=1)
    signal = RecoverySignal(
        component="agent",
        error="failed",
        attempts=1,
        metadata={"checkpoint": "available"},
    )
    decision = engine.evaluate(signal)
    assert decision.action is RecoveryAction.RESTORE
    assert engine.history[-1].metadata["checkpoint"] == "available"
