from aios_core.reasoning_engine import ReasoningEngine
def test(): s = ReasoningEngine().stats(); assert isinstance(s, dict)
