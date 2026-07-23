"""experiment_tracking test."""
def test(): from aios_core.experiment_tracking import ExperimentTracker; s = ExperimentTracker().stats(); assert isinstance(s, dict)
