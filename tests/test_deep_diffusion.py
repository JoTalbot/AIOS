"""Deep diffusion — mathematical properties."""
from aios_core.diffusion import DiffusionModel
def test_monotonic_noise():
    dm = DiffusionModel(timesteps=200)
    x = [1.0, 1.0, 1.0]
    noise_levels = []
    for t in [0, 50, 100, 150, 199]:
        r = dm.forward_process(x, t)
        noise = sum(abs(a-b) for a,b in zip(r, x))
        noise_levels.append(noise)
    assert noise_levels[0] <= noise_levels[-1]
def test_sample_statistics():
    dm = DiffusionModel()
    samples = dm.sample(1000)
    assert len(samples) == 1000
    mean = sum(samples) / len(samples)
    assert abs(mean) < 5.0
