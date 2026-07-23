from aios_core.planner import Planner
def test_validate():
    p = Planner()
    assert p.stats() is not None