"""test_score_based_scenario test."""
from aios_core.score_based import ScoreBasedModel

def test_score():
    s = ScoreBasedModel().stats()
    assert isinstance(s, dict)

