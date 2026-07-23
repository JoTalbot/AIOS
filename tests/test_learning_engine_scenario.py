from aios_core.learning_engine import LearningEngine
def test(): s = LearningEngine().stats(); assert isinstance(s, dict)
