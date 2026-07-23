from aios_core.ai_alignment import AIAlignment
def test_alignment():
    a = AIAlignment()
    assert a.check_alignment({'action': 'good'})['score'] == 1.0
    assert a.check_alignment({'action': 'use deception'})['score'] == 0.5