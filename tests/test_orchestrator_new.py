"""orchestrator test."""
def test(): from aios_core.orchestrator import Orchestrator; s = Orchestrator().stats(); assert isinstance(s, dict)
