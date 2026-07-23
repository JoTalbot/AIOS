"""Continuous learning full."""
from aios_core.continuous_learning import ContinuousLearner
def test(): s=ContinuousLearner().stats(); assert isinstance(s,dict)
