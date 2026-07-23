"""Integration test — AI advisor flow."""
from aios_core.ai_advisor import AISalesAdvisor
def test_advisor_creation():
    a = AISalesAdvisor()
    assert a is not None
