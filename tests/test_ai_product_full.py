from aios_core.ai_product_manager import AIProductManager
def test_pm():
    pm = AIProductManager()
    p = pm.create_product('App', 'vision')
    assert p['name'] == 'App'
    r = pm.create_roadmap(p, 2)
    assert len(r['milestones']) == 2