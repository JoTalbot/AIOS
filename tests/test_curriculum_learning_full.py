"""Curriculum learning full."""
from aios_core.curriculum_learning import CurriculumLearner
def test(): s=CurriculumLearner().stats(); assert isinstance(s,dict)
