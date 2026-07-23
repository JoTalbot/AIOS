"""Learning engine full ops."""
from aios_core.learning_engine import LearningEngine
def test_le(): assert LearningEngine().stats() is not None
