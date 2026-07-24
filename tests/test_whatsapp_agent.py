"""Tests for WhatsApp messenger agent — contact_manager, broadcast_scheduler, chat_analytics."""

from __future__ import annotations

from aios_core.modules.whatsapp import (
    WhatsAppStorage, ContactManager, Contact,
    BroadcastScheduler, BroadcastMessage, BroadcastStatus,
    ChatAnalyzer, ChatAnalytics,
)


def test_whatsapp_imports():
    """All WhatsApp module classes are importable."""
    assert WhatsAppStorage is not None
    assert ContactManager is not None
    assert BroadcastScheduler is not None
    assert ChatAnalyzer is not None


def test_contact_dataclass():
    """Contact dataclass stores all fields."""
    c = Contact(name="John", phone="+380991234567", jid="john@s.whatsapp.net", is_group=False)
    d = c.to_dict()
    assert d["name"] == "John"
    assert d["phone"] == "+380991234567"
    assert d["is_group"] is False


def test_contact_manager_add():
    """ContactManager adds a contact."""
    storage = WhatsAppStorage(":memory:")
    manager = ContactManager(storage)
    c = Contact(name="Alice", phone="+380991234568", jid="alice@s.whatsapp.net")
    assert manager.add_contact(c) is True


def test_contact_manager_list():
    """ContactManager lists contacts."""
    storage = WhatsAppStorage(":memory:")
    manager = ContactManager(storage)
    c = Contact(name="Bob", phone="+380991234569", jid="bob@s.whatsapp.net", tags=["vip"])
    manager.add_contact(c)

    contacts = manager.list_contacts()
    assert len(contacts) >= 1


def test_contact_manager_list_by_tag():
    """ContactManager filters contacts by tag."""
    storage = WhatsAppStorage(":memory:")
    manager = ContactManager(storage)
    c1 = Contact(name="VIP1", phone="+380991", jid="vip1@s.whatsapp.net", tags=["vip"])
    c2 = Contact(name="Regular1", phone="+380992", jid="reg1@s.whatsapp.net", tags=["regular"])
    manager.add_contact(c1)
    manager.add_contact(c2)

    vip_contacts = manager.list_contacts(tag="vip")
    assert len(vip_contacts) >= 1


def test_broadcast_scheduler_create():
    """BroadcastScheduler creates a draft broadcast."""
    storage = WhatsAppStorage(":memory:")
    scheduler = BroadcastScheduler(storage)
    msg = scheduler.create_broadcast("Hello from AIOS!", contact_tags=["vip"])
    assert msg.status == BroadcastStatus.DRAFT
    assert msg.text == "Hello from AIOS!"
    assert "vip" in msg.contact_tags


def test_broadcast_scheduler_approve():
    """BroadcastScheduler approves a broadcast."""
    storage = WhatsAppStorage(":memory:")
    scheduler = BroadcastScheduler(storage)
    msg = scheduler.create_broadcast("Test message")

    approved = scheduler.approve_broadcast(msg.id)
    assert approved is not None
    assert approved.status == BroadcastStatus.APPROVED


def test_broadcast_scheduler_list():
    """BroadcastScheduler lists broadcasts."""
    storage = WhatsAppStorage(":memory:")
    scheduler = BroadcastScheduler(storage)
    scheduler.create_broadcast("Msg 1")
    scheduler.create_broadcast("Msg 2")

    all_msgs = scheduler.list_broadcasts()
    assert len(all_msgs) >= 2

    drafts = scheduler.list_broadcasts(status=BroadcastStatus.DRAFT)
    assert len(drafts) >= 2


def test_broadcast_scheduler_cancel():
    """BroadcastScheduler cancels a broadcast."""
    storage = WhatsAppStorage(":memory:")
    scheduler = BroadcastScheduler(storage)
    msg = scheduler.create_broadcast("Cancel me")

    assert scheduler.cancel_broadcast(msg.id) is True
    assert msg.status == BroadcastStatus.FAILED


def test_chat_analyzer():
    """ChatAnalyzer computes analytics."""
    storage = WhatsAppStorage(":memory:")
    analyzer = ChatAnalyzer(storage, platform="whatsapp")
    analytics = analyzer.analytics()
    assert analytics.platform == "whatsapp"
    assert analytics.total_outbox_messages >= 0


def test_chat_analyzer_sentiment():
    """ChatAnalyzer computes sentiment summary."""
    storage = WhatsAppStorage(":memory:")
    analyzer = ChatAnalyzer(storage, platform="whatsapp")
    sentiment = analyzer.sentiment_summary()
    assert sentiment["platform"] == "whatsapp"
    assert "positive" in sentiment
    assert "total" in sentiment
