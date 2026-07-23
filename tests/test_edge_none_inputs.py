"""Edge case tests — None inputs."""
from aios_core.circuit_breaker import CircuitBreaker
from aios_core.self_healing import SelfHealing
from aios_core.advanced_security import AdvancedSecurity

def test_security_detect_threat_none():
    s = AdvancedSecurity()
    assert s.detect_threat({}) is False

def test_self_healing_no_strategy():
    sh = SelfHealing()
    assert sh.heal(RuntimeError("x")) is False
