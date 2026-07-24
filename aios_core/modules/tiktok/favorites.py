"""TikTok favorites — inherits RozetkaFavorites for product wishlists."""

from aios_core.modules.rozetka.favorites import RozetkaFavorites


class TikTokFavorites(RozetkaFavorites):
    """Favorites manager for TikTok Shop products.

    Inherits RozetkaFavorites with TikTok-specific behavior.
    """
