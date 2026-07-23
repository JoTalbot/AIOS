"""predictive_autonomy smoke test."""
def test_par(): from aios_core.predictive_autonomy import PredictiveAutonomyRegulator; assert PredictiveAutonomyRegulator().stats() is not None
