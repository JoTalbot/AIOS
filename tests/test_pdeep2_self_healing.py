"""Parametrized deep: self_healing."""
import pytest
from aios_core.self_healing import SelfHealing
@pytest.mark.parametrize("err",["ValueError","KeyError","IndexError"])
def test_sh(err):
    sh = SelfHealing()
    sh.register_strategy(err,lambda c:None)
    exc = {"ValueError":ValueError(),"KeyError":KeyError(),"IndexError":IndexError()}[err]
    assert sh.heal(exc) is True

