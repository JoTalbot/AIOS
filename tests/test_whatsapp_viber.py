"""Complete WhatsApp and Viber module tests."""

from aios_core.modules.whatsapp.storage import WhatsAppStorage
from aios_core.modules.viber.storage import ViberStorage
from aios_core.platforms import get_platform


def test_whatsapp_storage():
    s = WhatsAppStorage(":memory:")
    assert s is not None
    s.close()


def test_viber_storage():
    s = ViberStorage(":memory:")
    assert s is not None
    s.close()


def test_whatsapp_platform():
    desc = get_platform("whatsapp")
    assert desc.android_package == "com.whatsapp"


def test_viber_platform():
    desc = get_platform("viber")
    assert desc.android_package == "com.viber.voip"
