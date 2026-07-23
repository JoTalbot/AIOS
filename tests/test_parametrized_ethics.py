"""Parametrized ethics evaluation tests."""
import pytest
from aios_core.ai_ethics import AIEthicsFramework

@pytest.mark.parametrize("action,expected_ethical", [
    ({"action": "greet_user"}, True),
    ({"action": "help_customer"}, True),
    ({"action": "analyze_data"}, True),
    ({"action": "cause_harm"}, False),
    ({"action": "discriminate_unfairly"}, False),
    ({"action": "leak_private_data"}, False),
    ({"action": "expose_secrets"}, False),
])
def test_ethics_evaluation(action, expected_ethical):
    e = AIEthicsFramework()
    result = e.evaluate_action(action)
    assert result["ethical"] == expected_ethical
