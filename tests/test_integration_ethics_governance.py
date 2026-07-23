"""Integration: ethics + governance + alignment."""
from aios_core.ai_ethics import AIEthicsFramework
from aios_core.ai_governance import AIGovernance
from aios_core.ai_alignment import AIAlignment

def test_ethics_gov_alignment():
    ef = AIEthicsFramework()
    gov = AIGovernance()
    al = AIAlignment()
    r = ef.evaluate_action({"action": "test"})
    assert isinstance(r, dict)
    gov.add_policy("p1", {"rule": "x"})
    assert gov.stats()["policies"] == 1
    ar = al.check_alignment({"action": "test"})
    assert ar["score"] >= 0
