"""Parametrized self-healing tests."""

import pytest
from aios_core.self_healing import SelfHealing


@pytest.mark.parametrize("error_type,strategy_result,expected", [
    ("ValueError", True, True),
    ("KeyError", False, False),
    ("RuntimeError", None, False),
])
def test_heal_scenarios(error_type, strategy_result, expected):
    sh = SelfHealing()
    exc_map = {"ValueError": ValueError("v"), "KeyError": KeyError("k"), "RuntimeError": RuntimeError("r")}
    if error_type != "RuntimeError":
        sh.register_strategy(error_type, lambda ctx: strategy_result)
    assert sh.heal(exc_map[error_type]) == expected
