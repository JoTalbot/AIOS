"""time_series test."""
def test(): from aios_core.time_series import TimeSeriesAnalyzer; s = TimeSeriesAnalyzer().stats(); assert isinstance(s, dict)
