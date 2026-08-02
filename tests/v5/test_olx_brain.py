from aios_core.v5.agents.marketplace.brain import OLXIntelligenceBrain


def test_olx_brain_process():
    brain = OLXIntelligenceBrain()
    result = brain.process([])
    assert isinstance(result, dict)
