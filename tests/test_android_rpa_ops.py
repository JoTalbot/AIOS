"""Android RPA ops."""
from aios_core.android_rpa_bridge import AndroidRPAManager
def test_rpa(): assert AndroidRPAManager().stats() is not None
