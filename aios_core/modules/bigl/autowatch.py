"""Bigl.ua AutoWatch — inherits RozetkaAutoWatch."""

from aios_core.modules.rozetka.autowatch import RozetkaAutoWatch


class BiglAutoWatch(RozetkaAutoWatch):
    """AutoWatch cycle for Bigl.ua — inherits RozetkaAutoWatch."""

    def run_cycle(
        self, queries: list[str] | None = None, collect: bool = True
    ) -> dict[str, object]:
        """Run cycle with Bigl platform label."""
        report = super().run_cycle(queries=queries, collect=collect)
        report["platform"] = "bigl"
        return report
