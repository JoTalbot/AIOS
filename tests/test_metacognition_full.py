"""Metacognition full."""
from aios_core.metacognition import MetacognitionEngine
def test(): s=MetacognitionEngine().stats(); assert isinstance(s,dict)
