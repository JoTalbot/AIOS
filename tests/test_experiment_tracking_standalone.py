"""Experiment Tracking standalone test."""
from aios_core.experiment_tracking import ExperimentTracker
def test_init(): assert ExperimentTracker() is not None
