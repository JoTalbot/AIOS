"""RL deep scenario."""
from aios_core.reinforcement_learning import RLAgent
from aios_core.hierarchical_rl import HierarchicalRL
from aios_core.model_based_rl import ModelBasedRL
from aios_core.offline_rl import OfflineRL
from aios_core.multi_agent_rl import MultiAgentRL

def test_rl_stack():
    for cls in [RLAgent, HierarchicalRL, ModelBasedRL, OfflineRL, MultiAgentRL]:
        s = cls().stats()
        assert isinstance(s, dict)
