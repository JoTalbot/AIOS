import pytest

from execution.event_sink import ExecutionEventSink


def test_sink_rejects_invalid_target():
    sink = ExecutionEventSink(object())
    with pytest.raises(TypeError, match="callable or expose record"):
        sink.emit({"type": "execution.started"})


def test_sink_without_target_is_noop():
    assert ExecutionEventSink().emit({"type": "execution.started"}) is None


def test_sink_attach_replaces_target():
    events = []
    sink = ExecutionEventSink()
    assert sink.attach(events.append) is events.append
    sink.emit({"type": "execution.completed"})
    assert events == [{"type": "execution.completed"}]
