"""TikTok platform module (scaffolded onboarding package)."""

from .bootstrap import TikTokBootstrap
from .messenger import TikTokMessenger
from .storage import TikTokStorage

__all__ = [
    "TikTokBootstrap",
    "TikTokMessenger",
    "TikTokStorage",
]
