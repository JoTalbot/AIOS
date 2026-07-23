"""auto_scaler test."""
def test(): from aios_core.auto_scaler import AutoScaler; s = AutoScaler().stats(); assert isinstance(s, dict)
