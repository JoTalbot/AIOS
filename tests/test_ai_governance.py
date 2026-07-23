"""Tests for AI Governance module."""

from aios_core.ai_governance import AIGovernance


def test_add_policy():
    g = AIGovernance()
    g.add_policy("data_retention", {"max_days": 90, "encrypt": True})
    assert "data_retention" in g.policies
    assert g.policies["data_retention"]["max_days"] == 90


def test_audit_compliant():
    g = AIGovernance()
    result = g.audit({"state": "clean"})
    assert result["compliant"] is True
    assert result["violations"] == []


def test_stats():
    g = AIGovernance()
    g.add_policy("p1", {})
    g.audit({})
    g.audit({})
    s = g.stats()
    assert s["policies"] == 1
    assert s["audits"] == 2
