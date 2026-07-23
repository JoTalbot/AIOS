"""Parametrized: diffusion full."""
import pytest
from aios_core.diffusion import DiffusionModel

@pytest.mark.parametrize("timesteps", [10,50,100,500,1000])
def test_config_timesteps(timesteps):
    dm = DiffusionModel(timesteps=timesteps)
    assert dm.stats()["timesteps"] == timesteps
    assert len(dm.betas) == timesteps

@pytest.mark.parametrize("t", [0,10,50,99])
def test_forward_at_t(t):
    dm = DiffusionModel(timesteps=100)
    x = [0.5, 1.5, 2.5]
    r = dm.forward_process(x, t)
    assert len(r) == 3
    assert all(isinstance(v, float) for v in r)
