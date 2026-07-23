"""Score based full."""
from aios_core.score_based import ScoreBasedModel
def test(): s=ScoreBasedModel().stats(); assert isinstance(s,dict)
