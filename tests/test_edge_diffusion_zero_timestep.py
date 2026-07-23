"""Edge: diffusion at zero timestep."""
from aios_core.diffusion import DiffusionModel

def test_zero_timestep_no_change():
    dm = DiffusionModel(timesteps=100)
    x = [1.0, 2.0, 3.0]
    result = dm.forward_process(x, 0)
    for a, b in zip(result, x):
        assert abs(a - b) < 1.0
