"""RL full ops."""
from aios_core.reinforcement_learning import RLAgent
def test(): s=RLAgent().stats(); assert isinstance(s,dict)
