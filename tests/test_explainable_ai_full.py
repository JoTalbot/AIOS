"""XAI full ops."""
from aios_core.explainable_ai import ExplainableAI
def test_xai(): s=ExplainableAI().stats(); assert isinstance(s,dict)
