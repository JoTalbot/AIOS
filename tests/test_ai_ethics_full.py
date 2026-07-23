from aios_core.ai_ethics import AIEthicsFramework
def test_ethics_report():
    e = AIEthicsFramework()
    e.evaluate_action({'action': 'good'})
    e.evaluate_action({'action': 'bad_harm'})
    r = e.generate_ethics_report()
    assert r['total_assessments'] == 2
    assert r['average_ethical_score'] < 1.0