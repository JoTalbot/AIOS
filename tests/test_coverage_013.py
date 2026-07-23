"""Test scalable oversight."""
from aios_core.ai_safety_scalable_oversight import ScalableOversight
def test_oversight(): assert ScalableOversight().stats() is not None
