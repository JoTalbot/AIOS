"""Test recursive reward modeling."""
from aios_core.ai_safety_recursive_reward import RecursiveRewardModel
def test_reward(): assert RecursiveRewardModel().stats() is not None
