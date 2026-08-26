from core.runtime.message_lifecycle import MessageLifecycle


def test_message_lifecycle_passthrough():
    lifecycle = MessageLifecycle()
    assert lifecycle.handle('ping') == 'ping'
