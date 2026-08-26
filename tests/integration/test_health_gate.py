from core.runtime.health_gate import HealthGate


def test_health_gate_ready():
    assert HealthGate().check().ready
