"""Tests for AI Product Manager module."""

from aios_core.ai_product_manager import AIProductManager


def test_create_product():
    pm = AIProductManager()
    prod = pm.create_product("MyApp", "Simplify shopping")
    assert prod["name"] == "MyApp"
    assert prod["vision"] == "Simplify shopping"
    assert prod["status"] == "ideation"


def test_create_roadmap():
    pm = AIProductManager()
    prod = pm.create_product("App", "V1")
    roadmap = pm.create_roadmap(prod, quarters=2)
    assert roadmap["product"] == "App"
    assert roadmap["quarters"] == 2
    assert len(roadmap["milestones"]) == 2


def test_stats():
    pm = AIProductManager()
    prod = pm.create_product("P1", "v1")
    pm.create_roadmap(prod)
    pm.create_product("P2", "v2")
    s = pm.stats()
    assert s["products"] == 2
    assert s["roadmaps"] == 1
