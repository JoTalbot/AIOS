import pytest

from execution.event_sink import ExecutionEventSink


def test_event_sink_supports_record_method():
    events = []
    sink = ExecutionEventSink(events)
    with pytest.raises(TypeError):
        sink.emit({"type": "execution.completed"})

    sink.attach(events.append)
    event = {"type": "execution.completed"}
    assert sink.emit(event) is None
    assert events[-1] == event


def test_event_sink_supports_recording_object():
    class Recorder:
        def __init__(self):
            self.events = []

        def record(self, event):
            self.events.append(event)
            return event

    recorder = Recorder()
    sink = ExecutionEventSink(recorder)
    event = {"type": "execution.failed"}
    assert sink.emit(event) is event
    assert recorder.events == [event]
