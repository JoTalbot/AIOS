"""workflow standalone test."""
from aios_core.workflow import WorkflowEngine
def test_init(): s = WorkflowEngine().stats(); assert isinstance(s, dict)
