"""Model-based RL full."""
from aios_core.model_based_rl import ModelBasedRL
def test(): s=ModelBasedRL().stats(); assert isinstance(s,dict)
