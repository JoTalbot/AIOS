from aios_core.event_bus import EventBus
def test_multi_handler():
    eb = EventBus(); r = []
    eb.on('e', lambda p: r.append(1))
    eb.on('e', lambda p: r.append(2))
    eb.emit('e', {})
    assert len(r) == 2