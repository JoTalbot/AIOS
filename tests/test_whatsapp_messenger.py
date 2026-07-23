"""WhatsApp messenger tests."""
from aios_core.modules.whatsapp.messenger import WhatsAppMessenger
def test_messenger_exists():
    assert WhatsAppMessenger is not None
