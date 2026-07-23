"""State space full ops."""
from aios_core.state_space import StateSpaceModel
def test_ssm(): s=StateSpaceModel().stats(); assert isinstance(s,dict)
