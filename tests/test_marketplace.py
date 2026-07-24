"""Tests for CapabilityMarketplace v4.1"""

from aios_core import Database, Orchestrator


def test_publish_and_search():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    mp = orch.marketplace
    mp.publish(
        name="advanced_reasoner",
        description="Better reasoning capability",
        author="community",
        tags=["reasoning", "ai"],
    )

    results = mp.search("reasoner")
    assert len(results) >= 1
    assert results[0].name == "advanced_reasoner"


def test_download():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    item = orch.marketplace.publish("test_cap", "desc")
    result = orch.marketplace.download(item.id)

    assert result["success"] is True
    assert result["capability"].downloads == 1


def test_orchestrator_marketplace_stats():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    orch.marketplace.publish("demo", "test")
    stats = orch.stats()

    assert "marketplace" in stats["subsystems"]
    assert stats["subsystems"]["marketplace"]["total_capabilities"] >= 1
