"""Complete Prom, Bigl, Shafa platform tests."""

from aios_core.modules.prom import PromStorage
from aios_core.modules.bigl import BiglStorage
from aios_core.modules.shafa import ShafaStorage
from aios_core.platforms import get_platform


def test_prom_platform():
    desc = get_platform("prom")
    assert desc is not None


def test_bigl_platform():
    desc = get_platform("bigl")
    assert desc is not None


def test_shafa_platform():
    desc = get_platform("shafa")
    assert desc is not None


def test_all_platforms_registered():
    from aios_core.platforms import list_platforms
    names = {p.name for p in list_platforms()}
    assert "olx" in names
    assert "instagram" in names
    assert "facebook" in names
    assert "tiktok" in names
    assert "whatsapp" in names
    assert "viber" in names
