"""Tests for ConstitutionEvolver v4.0-alpha"""

from aios_core import Orchestrator, Database


def test_propose_article():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    article = orch.constitution_evolver.propose_article(
        title="ARTICLE-LXVIII — ETHICAL AI",
        principle="AI must act ethically and transparently.",
        laws=["Never harm humans", "Always explain decisions"],
        justification="Based on ethical guidelines.",
        confidence=0.9
    )

    assert article.id is not None
    assert article.status == "proposed"


def test_review_proposal():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    article = orch.constitution_evolver.propose_article("Test", "Principle", ["Law 1"])
    result = orch.constitution_evolver.review_proposal(article.id, "accept")

    assert result["success"] is True
    assert result["new_status"] == "accepted"


def test_generate_from_experience():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    experience = {"repeated_failure": True, "count": 12}
    article = orch.constitution_evolver.generate_article_from_experience(experience)

    assert article is not None
    assert "FAILURE" in article.title


def test_orchestrator_integration():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    stats = orch.stats()
    assert "constitution_evolver" in stats["subsystems"]