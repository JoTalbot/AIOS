"""Tests for execution kernel boundary."""

import pytest

from core.execution.boundary import ExecutionBoundary


class FakeRuntime:
    async def execute(self, context):
        return {"context": context}


class FailingRuntime:
    async def execute(self, context):
        raise RuntimeError("execution failed")


@pytest.mark.asyncio
async def test_execution_boundary_returns_result():
    boundary = ExecutionBoundary(FakeRuntime())

    result = await boundary.execute({"task": "demo"})

    assert result.success is True
    assert result.value == {"context": {"task": "demo"}}


@pytest.mark.asyncio
async def test_execution_boundary_normalizes_errors():
    boundary = ExecutionBoundary(FailingRuntime())

    result = await boundary.execute({"task": "demo"})

    assert result.success is False
    assert isinstance(result.error, RuntimeError)
