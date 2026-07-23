"""auto_scaler test."""
from aios_core.auto_scaler import AutoScaler
def test_init(): s = AutoScaler().stats(); assert isinstance(s, dict)
