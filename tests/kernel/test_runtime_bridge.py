"""Runtime bridge tests for AIOS v20."""

from aios.kernel.telemetry import Telemetry
from aios.kernel.distributed_context import DistributedContext


def test_telemetry_records_events():
    telemetry = Telemetry()
    event = telemetry.record("execution.started")
    assert event.name == "execution.started"


def test_distributed_context_propagation():
    context = DistributedContext(metadata={"task": "demo"})
    data = context.propagate()
    assert data["metadata"]["task"] == "demo"
