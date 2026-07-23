"""pinn smoke test."""
def test_pinn(): from aios_core.pinn import PhysicsInformedNN; s = PhysicsInformedNN().stats(); assert isinstance(s, dict)
