"""explainable_ai smoke test."""
def test_xai(): from aios_core.explainable_ai import ExplainableAI; assert ExplainableAI().stats() is not None
