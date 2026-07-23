"""test_pinn_scenario test."""
from aios_core.pinn import PhysicsInformedNN

def test_pinn():
    s = PhysicsInformedNN().stats()
    assert isinstance(s, dict)

