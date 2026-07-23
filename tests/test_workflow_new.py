"""workflow test."""
def test(): from aios_core.workflow import WorkflowEngine; s = WorkflowEngine().stats(); assert isinstance(s, dict)
