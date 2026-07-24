"""Prom.ua price tracker, autowatch, favorites — inherit Rozetka pattern."""

from aios_core.modules.rozetka.price_tracker import RozetkaPriceTracker
from aios_core.modules.rozetka.autowatch import RozetkaAutoWatch
from aios_core.modules.rozetka.favorites import RozetkaFavorites


class PromPriceTracker(RozetkaPriceTracker):
    """Price tracker for Prom.ua — inherits RozetkaPriceTracker."""


class PromAutoWatch(RozetkaAutoWatch):
    """AutoWatch for Prom.ua — inherits RozetkaAutoWatch."""

    def run_cycle(self, queries=None, collect=True) -> dict:
        """Run cycle with Prom platform label."""
        report = super().run_cycle(queries=queries, collect=collect)
        report["platform"] = "prom"
        return report


class PromFavorites(RozetkaFavorites):
    """Favorites for Prom.ua — inherits RozetkaFavorites."""
