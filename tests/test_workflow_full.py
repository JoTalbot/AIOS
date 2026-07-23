"""Workflow engine full."""
from aios_core.workflow import WorkflowEngine
def test(): s=WorkflowEngine().stats(); assert isinstance(s,dict)
