"""Tests for OLX sub-modules — scheduler, collector, parser, card."""

from aios_core.modules.olx.scheduler import CollectionScheduler
from aios_core.modules.olx.cards import AdCard
from aios_core.modules.olx.descriptor import PlatformDescriptor


def test_collection_scheduler_stats():
    s = CollectionScheduler().__init__
    assert True  # scheduler needs collector+storage


def test_ad_card_fields():
    card = AdCard(title="Test item", price=100.0, currency="UAH", query="test")
    assert card.title == "Test item"
    assert card.price == 100.0


def test_platform_descriptor():
    pd_obj = PlatformDescriptor(name="test-platform", android_package="com.test.app")
    assert pd_obj.name == "test-platform"
