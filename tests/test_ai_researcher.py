"""Tests for AI Researcher module."""

from aios_core.ai_researcher import AIResearcher


def test_write_paper():
    r = AIResearcher()
    paper = r.write_paper("NLP", [{"name": "exp1", "result": 0.95}])
    assert "NLP" in paper["title"]
    assert paper["status"] == "draft"
    assert len(paper["experiments"]) == 1


def test_peer_review():
    r = AIResearcher()
    paper = r.write_paper("RL", [])
    review = r.peer_review(paper)
    assert review["recommendation"] == "accept"
    assert review["score"] == 8.5


def test_stats():
    r = AIResearcher()
    r.write_paper("T1", [])
    r.write_paper("T2", [])
    assert r.stats()["papers"] == 2
