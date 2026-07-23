"""metacognition test."""
def test(): from aios_core.metacognition import MetacognitionEngine; s = MetacognitionEngine().stats(); assert isinstance(s, dict)
