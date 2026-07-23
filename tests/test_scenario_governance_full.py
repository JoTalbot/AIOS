"""Governance full scenario."""
from aios_core.ai_governance import AIGovernance
def test_gov_full():
    g = AIGovernance()
    policies = [("p1", {"r": 1}), ("p2", {"r": 2}), ("p3", {"r": 3})]
    for name, rules in policies:
        g.add_policy(name, rules)
    assert g.stats()["policies"] == 3
    for _ in range(5):
        r = g.audit({"state": "clean"})
        assert r["compliant"] is True
    assert g.stats()["audits"] == 5
