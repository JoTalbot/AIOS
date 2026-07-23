"""WhatsApp storage ops."""
from aios_core.modules.whatsapp.storage import WhatsAppStorage
def test(): s = WhatsAppStorage(":memory:"); assert s is not None; s.close()
