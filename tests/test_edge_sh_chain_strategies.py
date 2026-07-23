"""Edge: self-healing chain."""
from aios_core.self_healing import SelfHealing
def test_chain():
    sh = SelfHealing()
    log = []
    for err in ["ValueError","KeyError","IndexError"]:
        sh.register_strategy(err, lambda c, e=err: log.append(e))
    for exc in [ValueError(), KeyError(), IndexError()]:
        assert sh.heal(exc) is True
    assert len(log) == 3
