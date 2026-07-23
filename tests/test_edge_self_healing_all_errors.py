"""Edge: self-healing with all error types."""
from aios_core.self_healing import SelfHealing

def test_all_builtin_errors():
    sh = SelfHealing()
    for err in [ValueError(), KeyError(), TypeError(), RuntimeError(), IndexError()]:
        assert sh.heal(err) is False

def test_registered_then_heal():
    sh = SelfHealing()
    called = []
    sh.register_strategy("IndexError", lambda c: called.append(1))
    assert sh.heal(IndexError()) is True
    assert len(called) == 1
