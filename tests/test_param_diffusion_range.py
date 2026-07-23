import pytest
from aios_core.diffusion import DiffusionModel

@pytest.mark.parametrize("t", [0,1,5,10,50,99])
def test_forward_at_timestep(t):
    dm = DiffusionModel(timesteps=100)
    x = [1.0, 2.0, 3.0]
    r = dm.forward_process(x, t)
    assert len(r) == 3

@pytest.mark.parametrize("size", [1,5,10,100,1000])
def test_sample_sizes(size):
    dm = DiffusionModel()
    assert len(dm.sample(size)) == size
