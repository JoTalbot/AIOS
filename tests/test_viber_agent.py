"""Tests for Viber messenger agent — inherits WhatsApp modules."""

from __future__ import annotations

from aios_core.modules.viber import (
    ViberBroadcastScheduler,
    ViberChatAnalyzer,
    ViberContactManager,
    ViberStorage,
)
from aios_core.modules.whatsapp.contact_manager import Contact


def test_viber_imports():
    """All Viber module classes are importable."""
    assert ViberStorage is not None
    assert ViberContactManager is not None
    assert ViberBroadcastScheduler is not None
    assert ViberChatAnalyzer is not None


def test_viber_storage_inherits_olx():
    """ViberStorage inherits OLXStorage."""
    from aios_core.modules.olx.storage import OLXStorage
    assert issubclass(ViberStorage, OLXStorage)


def test_viber_contact_manager():
    """ViberContactManager inherits WhatsApp ContactManager."""
    storage = ViberStorage(":memory:")
    manager = ViberContactManager(storage)
    c = Contact(name="ViberUser", phone="+380991234567", jid="viber_user")
    assert manager.add_contact(c) is True


def test_viber_broadcast_scheduler():
    """ViberBroadcastScheduler creates broadcasts."""
    storage = ViberStorage(":memory:")
    scheduler = ViberBroadcastScheduler(storage)
    msg = scheduler.create_broadcast("Hello Viber!")
    assert msg is not None
    assert msg.text == "Hello Viber!"


def test_viber_chat_analyzer():
    """ViberChatAnalyzer computes analytics for viber platform."""
    storage = ViberStorage(":memory:")
    analyzer = ViberChatAnalyzer(storage)
    analytics = analyzer.analytics()
    assert analytics.platform == "viber"

def test_viber_sentiment():
    """ViberChatAnalyzer computes sentiment."""
    storage = ViberStorage(":memory:")
    analyzer = ViberChatAnalyzer(storage)
    sentiment = analyzer.sentiment_summary()
    assert sentiment["platform"] == "viber"
