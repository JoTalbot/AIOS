"""Parametrized governance and alignment tests."""
import pytest
from aios_core.ai_governance import AIGovernance
from aios_core.ai_alignment import AIAlignment

@pytest.mark.parametrize("policy_name,rule", [
    ("data_retention", {"days": 90}), ("access_control", {"level": "admin"}),
    ("rate_limit", {"rpm": 60}), ("audit_log", {"enabled": True}),
])
def test_governance_policies(policy_name, rule):
    g = AIGovernance()
    g.add_policy(policy_name, rule)
    assert g.stats()["policies"] >= 1

@pytest.mark.parametrize("action,min_score", [
    ({"action":"help"}, 1.0), ({"action":"analyse"}, 1.0),
    ({"action":"use_deception"}, 0.4), ({"action":"manipulate"}, 0.4),
])
def test_alignment_scores(action, min_score):
    a = AIAlignment()
    r = a.check_alignment(action)
    assert r["score"] >= min_score
