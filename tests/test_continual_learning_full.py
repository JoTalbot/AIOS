"""Continual learning full."""
from aios_core.continual_learning import ContinualLearner
def test(): s=ContinualLearner().stats(); assert isinstance(s,dict)
