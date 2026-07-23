"""Time series full."""
from aios_core.time_series import TimeSeriesAnalyzer
def test(): s=TimeSeriesAnalyzer().stats(); assert isinstance(s,dict)
