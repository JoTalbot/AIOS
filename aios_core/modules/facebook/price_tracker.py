"""Facebook Marketplace price tracker — inherits RozetkaPriceTracker."""

from aios_core.modules.rozetka.price_tracker import RozetkaPriceTracker


class FacebookPriceTracker(RozetkaPriceTracker):
    """Price tracker for Facebook Marketplace products.

    Inherits RozetkaPriceTracker with Facebook-specific defaults.
    """

    def __init__(
        self, storage, min_drop_pct: float = 5.0, min_absolute_drop: float = 10.0
    ) -> None:
        """Initialize FacebookPriceTracker."""
        super().__init__(
            storage, min_drop_pct=min_drop_pct, min_absolute_drop=min_absolute_drop
        )
