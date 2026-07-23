"""Parametrized deep: adversarial."""
import pytest
from aios_core.adversarial import AdversarialDefense
@pytest.mark.parametrize("data,exp",[([0.0,1.0],True),([0.1,0.2],False)])
def test_adv(data,exp): assert AdversarialDefense().detect_adversarial(data,0.3)==exp

