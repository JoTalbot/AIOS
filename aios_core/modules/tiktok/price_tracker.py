"""TikTok price tracker — inherits RozetkaPriceTracker with TikTok-specific defaults."""

from aios_core.modules.rozetka.price_tracker import RozetkaPriceTracker


class TikTokPriceTracker(RozetkaPriceTracker):
    """Price tracker for TikTok Shop products.

    Inherits RozetkaPriceTracker with TikTok-specific defaults.
    TikTok uses different price patterns (flash sales, coupon codes)
    which may override detection thresholds.
    """

    def __init__(self, storage, min_drop_pct: float = 10.0, min_absolute_drop: float = 5.0) -> None:
        """Initialize TikTokPriceTracker.

        Args:
            storage: TikTokStorage instance.
            min_drop_pct: Default 10% for TikTok (flash sales cause bigger drops).
            min_absolute_drop: Default 5 UAH.
        """
        super().__init__(storage, min_drop_pct=min_drop_pct, min_absolute_drop=min_absolute_drop)
