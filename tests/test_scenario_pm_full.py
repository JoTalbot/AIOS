"""PM full scenario."""
from aios_core.ai_product_manager import AIProductManager
def test_pm_full():
    pm = AIProductManager()
    products = [("A","va"), ("B","vb"), ("C","vc")]
    for name, vision in products:
        p = pm.create_product(name, vision)
        pm.create_roadmap(p, quarters=4)
    assert pm.stats()["products"] == 3
    assert pm.stats()["roadmaps"] == 3
