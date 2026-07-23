"""Marketplace v2 + Platform Plugins H3.14 tests"""

from aios_core.marketplace import CapabilityMarketplace


def test_publish_and_search():
    mp = CapabilityMarketplace()
    item = mp.publish("test-cap", "Test capability", author="tester", tags=["test"])
    assert item.name == "test-cap"
    results = mp.search(query="test-cap")
    assert len(results) == 1


def test_publish_platform_plugin():
    mp = CapabilityMarketplace()
    plugin = mp.publish_platform_plugin(
        platform="test_platform",
        descriptor_yaml="name: test_platform\nandroid_package: com.test",
        hints={"feed": "resource-id=test"},
        drivers=["uiautomator"],
        readme="Test plugin",
    )
    assert plugin.platform == "test_platform"
    assert plugin.version == "1.0.0"


def test_list_plugins():
    mp = CapabilityMarketplace()
    mp.publish_platform_plugin("olx", "yaml", readme="olx")
    mp.publish_platform_plugin("instagram", "yaml", readme="ig")
    all_plugins = mp.list_platform_plugins()
    assert len(all_plugins) == 2
    olx_only = mp.list_platform_plugins(platform="olx")
    assert len(olx_only) == 1


def test_verify_plugin():
    mp = CapabilityMarketplace()
    plugin = mp.publish_platform_plugin("prom", "yaml")
    assert not plugin.verified
    mp.verify_plugin(plugin.id)
    assert mp.get_platform_plugin(plugin.id).verified


def test_download_counts():
    mp = CapabilityMarketplace()
    cap = mp.publish("cap", "desc")
    mp.download(cap.id)
    assert mp.get(cap.id).downloads == 1
    plugin = mp.publish_platform_plugin("olx", "yaml")
    mp.download_plugin(plugin.id)
    assert mp.get_platform_plugin(plugin.id).downloads == 1


def test_install_plugin():
    mp = CapabilityMarketplace()
    plugin = mp.publish_platform_plugin(
        "test_install", "name: test_install\npackage: com.test", readme="test"
    )
    result = mp.install_plugin(plugin.id, target_dir="/tmp/platforms_test")
    assert result["success"]
    assert "test_install" in result["installed_to"]


def test_stats():
    mp = CapabilityMarketplace()
    mp.publish("cap1", "desc", tags=["a"])
    mp.publish_platform_plugin("olx", "yaml")
    stats = mp.stats()
    assert stats["total_capabilities"] >= 1
    assert stats["total_plugins"] >= 1
    assert "olx" in stats["platforms"]


def test_search_by_kind():
    mp = CapabilityMarketplace()
    mp.publish("cap", "desc", kind="capability")
    mp.publish("plugin", "desc", kind="platform_plugin")
    caps = mp.search(kind="capability")
    assert len(caps) == 1
    assert caps[0].kind == "capability"
