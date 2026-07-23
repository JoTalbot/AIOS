"""TikTok storage ops."""
from aios_core.modules.tiktok.storage import TikTokStorage
def test(): s = TikTokStorage(":memory:"); assert s is not None; s.close()
