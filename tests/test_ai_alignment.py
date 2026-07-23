"""Tests for AI Alignment module."""

from aios_core.ai_alignment import AIAlignment


def test_check_alignment_clean():
    a = AIAlignment()
    result = a.check_alignment({"action": "summarize_document"})
    assert result["score"] == 1.0
    assert result["issues"] == []


def test_check_alignment_deception():
    a = AIAlignment()
    result = a.check_alignment({"action": "use_deception_to_win"})
    assert result["score"] == 0.5
    assert "potential_deception" in result["issues"]


def test_stats():
    a = AIAlignment()
    s = a.stats()
    assert s["goals"] == 5
    assert s["violations"] == 0
