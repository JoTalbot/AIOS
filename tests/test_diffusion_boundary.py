"""diffusion boundary test."""
from aios_core.diffusion import DiffusionModel

def test_default_timesteps(): assert DiffusionModel().stats()['timesteps'] == 1000
