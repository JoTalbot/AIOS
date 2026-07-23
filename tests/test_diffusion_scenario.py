"""test_diffusion_scenario test."""
from aios_core.diffusion import DiffusionModel

def test_denoising_progression():
    dm = DiffusionModel(timesteps=100)
    x = [1.0, 2.0, 3.0]
    noisy = dm.forward_process(x, 90)
    clean = dm.forward_process(x, 5)
    diff_noisy = sum(abs(a-b) for a,b in zip(noisy, x))
    diff_clean = sum(abs(a-b) for a,b in zip(clean, x))
    assert diff_noisy > diff_clean
