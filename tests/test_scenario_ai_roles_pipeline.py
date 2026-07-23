"""AI roles pipeline — engineer, PM, researcher."""
from aios_core.ai_engineer import AIEngineer
from aios_core.ai_product_manager import AIProductManager
from aios_core.ai_researcher import AIResearcher

def test_ai_team():
    eng = AIEngineer()
    pm = AIProductManager()
    res = AIResearcher()
    design = eng.design_system({"name": "ProductX"})
    assert design["name"] == "ProductX"
    prod = pm.create_product("ProductX", "vision")
    assert prod["name"] == "ProductX"
    roadmap = pm.create_roadmap(prod, quarters=4)
    assert len(roadmap["milestones"]) == 4
    paper = res.write_paper("ProductX AI", [])
    assert paper["status"] == "draft"
