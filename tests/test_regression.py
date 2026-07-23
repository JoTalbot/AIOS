"""Tests for platform regression detection."""
from aios_core.platforms.regression import RegressionChecker
def test_regression_init():
    rc = RegressionChecker()
    assert rc is not None
