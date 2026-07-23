"""Auto scaler full."""
from aios_core.auto_scaler import AutoScaler
def test(): s=AutoScaler().stats(); assert isinstance(s,dict)
