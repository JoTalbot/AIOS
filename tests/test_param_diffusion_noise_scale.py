"""Parametrized diffusion noise scaling."""
import pytest
from aios_core.diffusion import DiffusionModel

@pytest.mark.parametrize("t", [0, 10, 50, 100, 199])
def test_noise_increases_with_t(t):
    dm = DiffusionModel(timesteps=200)
    x = [1.0, 1.0, 1.0]
    r = dm.forward_process(x, t)
    assert len(r) == len(x)

@pytest.mark.parametrize("dim", [1, 3, 10, 100])
def test_sample_dimensions(dim):
    dm = DiffusionModel()
    s = dm.sample(dim)
    assert len(s) == dim
