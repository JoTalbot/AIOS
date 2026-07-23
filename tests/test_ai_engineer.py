"""Tests for AI Engineer module."""

from aios_core.ai_engineer import AIEngineer


def test_design_system():
    eng = AIEngineer()
    design = eng.design_system({"name": "PaymentService"})
    assert design["name"] == "PaymentService"
    assert design["architecture"] == "modular microservices"
    assert design["status"] == "designed"
    assert "api" in design["components"]


def test_implement_from_design():
    eng = AIEngineer()
    design = eng.design_system({"name": "Auth"})
    codebase = eng.implement(design)
    assert codebase["system"] == "Auth"
    assert codebase["files"] == 150
    assert codebase["coverage"] == 0.92


def test_stats():
    eng = AIEngineer()
    eng.design_system({"name": "X"})
    eng.design_system({"name": "Y"})
    eng.implement({"name": "X"})
    s = eng.stats()
    assert s["systems"] == 2
    assert s["codebases"] == 1
