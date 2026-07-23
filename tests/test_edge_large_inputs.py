"""Edge case tests — large inputs."""
from aios_core.ab_testing import ABTest
from aios_core.diffusion import DiffusionModel

def test_ab_assign_many_users():
    ab = ABTest("test", {"a": 0.5, "b": 0.5})
    results = [ab.assign_variant(f"user{i}") for i in range(1000)]
    assert all(v in ("a", "b") for v in results)

def test_diffusion_large_sample():
    dm = DiffusionModel(timesteps=10)
    s = dm.sample(10000)
    assert len(s) == 10000
