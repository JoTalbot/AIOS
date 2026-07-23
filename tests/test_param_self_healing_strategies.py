import pytest
from aios_core.self_healing import SelfHealing

@pytest.mark.parametrize("err_type,has_strategy", [
    ("ValueError", True), ("KeyError", True), ("RuntimeError", False),
])
def test_heal_or_not(err_type, has_strategy):
    sh = SelfHealing()
    if has_strategy:
        sh.register_strategy(err_type, lambda c: None)
    exc_map = {"ValueError": ValueError(), "KeyError": KeyError(), "RuntimeError": RuntimeError()}
    assert sh.heal(exc_map[err_type]) == has_strategy
