"""TikTok AutoWatch — inherits RozetkaAutoWatch with video-content focus."""

from aios_core.modules.rozetka.autowatch import RozetkaAutoWatch


class TikTokAutoWatch(RozetkaAutoWatch):
    """AutoWatch cycle for TikTok Shop products.

    Inherits RozetkaAutoWatch with TikTok-specific extensions:
    - Video content trending detection
    - Product tag monitoring
    - Creator/seller tracking
    """

    def run_cycle(
        self, queries: list[str] | None = None, collect: bool = True
    ) -> dict[str, object]:
        """Run one full AutoWatch cycle for TikTok.

        Adds TikTok-specific 'video_trending' section to the report.
        """
        report = super().run_cycle(queries=queries, collect=collect)
        report["platform"] = "tiktok"

        # TikTok-specific: trending hashtags from recent products
        ads = self.storage.get_ads()
        trending_tags: list[str] = []
        for ad in ads:
            if ad.raw_texts:
                import re

                for text in ad.raw_texts:
                    tags = re.findall(r"#(\w+)", text)
                    trending_tags.extend(tags)

        # Count tag frequency
        from collections import Counter

        tag_counts = Counter(trending_tags)
        report["trending_hashtags"] = [
            {"tag": tag, "count": count} for tag, count in tag_counts.most_common(10)
        ]

        return report
