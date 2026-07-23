"""Parametrized deep: diffusion."""
import pytest
from aios_core.diffusion import DiffusionModel
@pytest.mark.parametrize("t",[0,5,10,25,50])
def test_diff(t):
    dm = DiffusionModel(100)
    x = [1.0,2.0,3.0]
    r = dm.forward_process(x,t)
    assert len(r)==3

