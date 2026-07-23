from aios_core.orchestrator import Orchestrator
def test_execute():
    o = Orchestrator()
    assert o.stats() is not None