"""WhatsApp operations tests."""
from aios_core.modules.whatsapp.bootstrap import WhatsAppBootstrap
from aios_core.modules.whatsapp.messenger import WhatsAppMessenger
def test_whatsapp_tools():
    assert WhatsAppBootstrap is not None
