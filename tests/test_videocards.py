"""Tests for video cards and reels scout."""

from aios_core.platforms.videocards import VideoCardParser
from aios_core.platforms.reelscout import ReelsCollector


def test_video_card_parser_init():
    vp = VideoCardParser()
    assert vp is not None


def test_reels_collector_init():
    rc = ReelsCollector()
    assert rc is not None
