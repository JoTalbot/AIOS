import pytest

from execution.event_sink import ExecutionEventSink


def test_sink_rejects_invalid_target():
    sink = ExecutionEventSink(object())
    with pytest.raises(TypeError, match="callable or expose record"):
        sink.emit({"type": "execution.started"})


def test_sink_without_target_is_noop():
    assert ExecutionEventSink().emit({"type": "execution.started"}) is None
