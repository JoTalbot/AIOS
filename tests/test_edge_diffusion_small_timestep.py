"""Edge: diffusion tiny timesteps."""
from aios_core.diffusion import DiffusionModel
def test_small_timesteps():
    dm = DiffusionModel(timesteps=3)
    x = [1.0, 2.0]
    r = dm.forward_process(x, 1)
    assert len(r) == 2
