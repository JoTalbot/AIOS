from aios_core.ai_governance import AIGovernance
def test_gov():
    g = AIGovernance()
    g.add_policy('test', {'rule': 'x'})
    assert g.stats()['policies'] == 1