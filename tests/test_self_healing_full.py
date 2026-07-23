"""Full tests for self-healing system."""

from aios_core.self_healing import SelfHealing


def test_register_and_heal():
    sh = SelfHealing()
    healed = []
    sh.register_strategy("ValueError", lambda ctx: healed.append(ctx))
    result = sh.heal(ValueError("test"), {"detail": "info"})
    assert result is True
    assert len(healed) == 1


def test_unregistered_error():
    sh = SelfHealing()
    result = sh.heal(RuntimeError("unknown"))
    assert result is False


def test_strategy_fails_gracefully():
    sh = SelfHealing()
    def failing_strategy(ctx):
        raise RuntimeError("recovery failed")
    sh.register_strategy("KeyError", failing_strategy)
    result = sh.heal(KeyError("bad_key"))
    assert result is False
