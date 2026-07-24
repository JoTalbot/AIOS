"""Facebook Marketplace AutoWatch — inherits RozetkaAutoWatch."""

from aios_core.modules.rozetka.autowatch import RozetkaAutoWatch


class FacebookAutoWatch(RozetkaAutoWatch):
    """AutoWatch cycle for Facebook Marketplace products.

    Inherits RozetkaAutoWatch with Facebook-specific behavior.
    """

    def run_cycle(
        self, queries: list[str] | None = None, collect: bool = True
    ) -> dict[str, object]:
        """Run one full AutoWatch cycle for Facebook Marketplace."""
        report = super().run_cycle(queries=queries, collect=collect)
        report["platform"] = "facebook"
        return report
