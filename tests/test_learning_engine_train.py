"""Learning engine train ops."""
from aios_core.learning_engine import LearningEngine
def test_le(): s = LearningEngine().stats(); assert isinstance(s, dict)
