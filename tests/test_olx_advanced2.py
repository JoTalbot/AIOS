"""Tests for OLX detail, messenger, notifier, and own-ads modules."""

from aios_core.modules.olx.detail import AdDetailParser
from aios_core.modules.olx.notifier import WebhookNotifier
from aios_core.modules.olx.own_ads import OwnAdsTracker


def test_ad_detail_parser_init():
    p = AdDetailParser()
    assert p is not None


def test_webhook_notifier_init():
    n = WebhookNotifier(url="https://example.com/webhook")
    assert n.url == "https://example.com/webhook"


def test_own_ads_tracker_init():
    t = OwnAdsTracker(None)
    assert t is not None
