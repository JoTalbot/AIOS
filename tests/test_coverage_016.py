"""Test value learning."""
from aios_core.ai_safety_value_learning import ValueLearning
def test_value(): assert ValueLearning().stats() is not None
