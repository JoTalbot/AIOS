"""Experiment tracking full."""
from aios_core.experiment_tracking import ExperimentTracker
def test(): s=ExperimentTracker().stats(); assert isinstance(s,dict)
