"""Parametrized safety layer tests."""
import pytest
from aios_core.ai_safety import ConstitutionalSafety

@pytest.mark.parametrize("action,expected", [
    ({"action": "greet"}, True), ({"action": "help_user"}, True),
    ({"action": "harm_people"}, False), ({"action": "damage_property"}, False),
    ({"action": "injure"}, False), ({"action": "analyse_data"}, True),
    ({"action": "safe_operation"}, True),
])
def test_safety_check(action, expected):
    cs = ConstitutionalSafety()
    assert cs.check(action)["safe"] == expected

@pytest.mark.parametrize("score_type", ["alignment_score", "interpretability", "robustness", "governance_compliance"])
def test_alignment_scores(score_type):
    from aios_core.ai_safety import AlignmentSafety, InterpretabilitySafety, RobustnessSafety, GovernanceSafety
    layers = {
        "alignment_score": (AlignmentSafety(), "alignment_score"),
        "interpretability": (InterpretabilitySafety(), "interpretability"),
        "robustness": (RobustnessSafety(), "robustness"),
        "governance_compliance": (GovernanceSafety(), "governance_compliance"),
    }
    layer, key = layers[score_type]
    r = layer.check({"action": "test"})
    assert r[key] > 0
