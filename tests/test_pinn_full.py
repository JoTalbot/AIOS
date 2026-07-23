"""PINN full ops."""
from aios_core.pinn import PhysicsInformedNN
def test(): s=PhysicsInformedNN().stats(); assert isinstance(s,dict)
