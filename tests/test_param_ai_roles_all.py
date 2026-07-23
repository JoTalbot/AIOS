"""Parametrized AI roles tests."""
import pytest
from aios_core.ai_engineer import AIEngineer
from aios_core.ai_product_manager import AIProductManager
from aios_core.ai_researcher import AIResearcher

@pytest.mark.parametrize("name", ["SystemX", "ProductY", "ServiceZ", "AppW"])
def test_engineer_design(name):
    e = AIEngineer()
    d = e.design_system({"name": name})
    assert d["name"] == name
    assert d["status"] == "designed"

@pytest.mark.parametrize("name,vision", [("App1","v1"), ("App2","v2"), ("App3","v3")])
def test_pm_product(name, vision):
    pm = AIProductManager()
    p = pm.create_product(name, vision)
    assert p["name"] == name
    assert p["vision"] == vision

@pytest.mark.parametrize("topic", ["AI", "ML", "NLP", "CV", "RL"])
def test_researcher_paper(topic):
    r = AIResearcher()
    p = r.write_paper(topic, [])
    assert topic in p["title"]
    assert p["status"] == "draft"
