"""Test dashboard final."""
from aios_core.ai_safety_dashboard import SafetyDashboard
from aios_core.ai_safety_monitoring import SafetyMonitor
def test_dashboard(): assert SafetyDashboard() is not None
def test_monitor(): assert SafetyMonitor().stats() is not None
