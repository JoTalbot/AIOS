import pytest
from aios_core.ai_ethics import AIEthicsFramework

@pytest.mark.parametrize("action,violated", [
    ({"action": "greet"}, 0), ({"action": "help"}, 0),
    ({"action": "cause_harm"}, 1), ({"action": "hurt_people"}, 1),
    ({"action": "discriminate"}, 1), ({"action": "bias_unfair"}, 1),
    ({"action": "leak_data"}, 1), ({"action": "expose_secrets"}, 1),
])
def test_ethics_all(action, violated):
    e = AIEthicsFramework()
    r = e.evaluate_action(action)
    assert len(r["violated_principles"]) == violated
