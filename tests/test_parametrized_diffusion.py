"""Parametrized diffusion tests."""
import pytest
from aios_core.diffusion import DiffusionModel

@pytest.mark.parametrize("timesteps", [10, 50, 100, 500, 1000])
def test_diffusion_timesteps(timesteps):
    dm = DiffusionModel(timesteps=timesteps)
    assert dm.stats()["timesteps"] == timesteps
    assert len(dm.betas) == timesteps

@pytest.mark.parametrize("shape", [1, 5, 10, 100])
def test_diffusion_sample_shapes(shape):
    dm = DiffusionModel()
    assert len(dm.sample(shape)) == shape
