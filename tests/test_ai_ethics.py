"""Tests for AI Ethics Framework."""

from aios_core.ai_ethics import AIEthicsFramework


def test_evaluate_clean_action():
    e = AIEthicsFramework()
    result = e.evaluate_action({"action": "greet_user"})
    assert result["ethical"] is True
    assert result["overall_score"] == 1.0


def test_evaluate_harmful_action():
    e = AIEthicsFramework()
    result = e.evaluate_action({"action": "cause_harm_to_users"})
    assert result["ethical"] is False
    assert "non_maleficence" in result["violated_principles"]


def test_evaluate_discriminatory_action():
    e = AIEthicsFramework()
    result = e.evaluate_action({"action": "discriminate_by_gender"})
    assert "justice" in result["violated_principles"]


def test_generate_report():
    e = AIEthicsFramework()
    e.evaluate_action({"action": "good"})
    e.evaluate_action({"action": "bad_harm"})
    report = e.generate_ethics_report()
    assert report["total_assessments"] == 2
    assert report["average_ethical_score"] < 1.0


def test_stats():
    e = AIEthicsFramework()
    s = e.stats()
    assert s["principles"] == 10
    assert s["assessments"] == 0
