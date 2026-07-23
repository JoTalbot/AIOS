"""test_self_healing_scenario test."""
from aios_core.self_healing import SelfHealing

def test_multiple_strategies():
    sh = SelfHealing()
    results = []
    sh.register_strategy("ValueError", lambda ctx: results.append("v"))
    sh.register_strategy("KeyError", lambda ctx: results.append("k"))
    assert sh.heal(ValueError()) is True
    assert results == ["v"]
    assert sh.heal(KeyError()) is True
    assert results == ["v", "k"]
