"""telemetry boundary test."""
from aios_core.telemetry import Telemetry

def test(): assert Telemetry().stats() is not None
