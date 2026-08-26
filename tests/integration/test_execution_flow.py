"""Integration tests for AIOS execution path."""


def test_execution_flow_import():
    from core.integration.execution_flow import ExecutionFlow
    assert ExecutionFlow is not None
