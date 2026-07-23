"""score_based smoke test."""
def test_sbm(): from aios_core.score_based import ScoreBasedModel; s = ScoreBasedModel().stats(); assert isinstance(s, dict)
