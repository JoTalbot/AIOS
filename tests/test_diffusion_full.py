"""Full tests for diffusion model forward process and sampling."""

from aios_core.diffusion import DiffusionModel


def test_diffusion_forward():
    dm = DiffusionModel(timesteps=100)
    x = [1.0, 2.0, 3.0]
    result = dm.forward_process(x, t=10)
    assert len(result) == 3


def test_diffusion_sample():
    dm = DiffusionModel()
    sample = dm.sample(5)
    assert len(sample) == 5


def test_diffusion_stats():
    dm = DiffusionModel(timesteps=500)
    assert dm.stats()["timesteps"] == 500
