"""Diffusion model ops."""
from aios_core.diffusion import DiffusionModel
def test_diff(): dm = DiffusionModel(100); x = [1.0,2.0]; r = dm.forward_process(x,10); assert len(r)==2
