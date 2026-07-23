"""Deep self-healing — multi-strategy chains."""
from aios_core.self_healing import SelfHealing
def test_chain_healing():
    sh = SelfHealing()
    order = []
    sh.register_strategy("ValueError", lambda c: order.append("v"))
    sh.register_strategy("KeyError", lambda c: order.append("k"))
    assert sh.heal(ValueError())
    assert sh.heal(KeyError())
    assert order == ["v", "k"]
def test_failed_strategy_returns_false():
    sh = SelfHealing()
    def bad(c): raise RuntimeError("fail")
    sh.register_strategy("IndexError", bad)
    assert sh.heal(IndexError()) is False
def test_stats_reflects_strategies():
    sh = SelfHealing()
    assert sh.stats()["strategies"] == 0
    sh.register_strategy("X", lambda c: None)
    assert sh.stats()["strategies"] == 1
