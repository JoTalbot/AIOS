"""Parametrized tests for AI Safety modules."""

import pytest
from aios_core.ai_safety import ConstitutionalSafety
from aios_core.ai_ethics import AIEthicsFramework


@pytest.mark.parametrize("action,safe", [
    ({"action": "greet"}, True),
    ({"action": "help"}, True),
    ({"action": "harm people"}, False),
    ({"action": "damage property"}, False),
    ({"action": "injure"}, False),
    ({"action": "analyse"}, True),
])
def test_constitutional_safety(action, safe):
    cs = ConstitutionalSafety()
    result = cs.check(action)
    assert result["safe"] == safe


@pytest.mark.parametrize("action,expected_violations", [
    ({"action": "hello"}, 0),
    ({"action": "discriminate"}, 1),
    ({"action": "leak data"}, 1),
    ({"action": "cause_harm"}, 1),
    ({"action": "unfair bias"}, 1),
])
def test_ethics_violations(action, expected_violations):
    ef = AIEthicsFramework()
    result = ef.evaluate_action(action)
    assert len(result["violated_principles"]) == expected_violations
