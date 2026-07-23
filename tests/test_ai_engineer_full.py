from aios_core.ai_engineer import AIEngineer
def test_eng():
    e = AIEngineer()
    d = e.design_system({'name': 'X'})
    assert d['name'] == 'X'
    impl = e.implement(d)
    assert impl['system'] == 'X'