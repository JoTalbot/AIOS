"""Android observability ops."""
from aios_core.android_observability import AndroidObservability
def test_obs(): ao = AndroidObservability("d1"); assert ao.stats() is not None
