"""Tests for aios_core/scraping_strategy_templates.py"""
from __future__ import annotations
import pytest
from aios_core.scraping_strategy_templates import StrategyTemplate, StrategyTemplateRegistry, StrategyKind


@pytest.fixture()
def registry():
    return StrategyTemplateRegistry()


class TestStrategyTemplate:
    def test_create(self):
        t = StrategyTemplate(template_id="t1", name="olx_basic", platform="olx")
        assert t.name == "olx_basic"

    def test_to_dict(self):
        t = StrategyTemplate(template_id="t1", name="t1", platform="olx")
        d = t.to_dict()
        assert isinstance(d, dict)


class TestStrategyTemplateRegistry:
    def test_register(self, registry):
        t = StrategyTemplate(template_id="t1", name="t1", platform="olx")
        registry.register(t)

    def test_get(self, registry):
        t = StrategyTemplate(template_id="t1", name="t1", platform="olx")
        registry.register(t)
        fetched = registry.get("t1")
        assert fetched is not None

    def test_get_nonexistent(self, registry):
        assert registry.get("nope") is None

    def test_list_templates(self, registry):
        registry.register(StrategyTemplate(template_id="t1", name="t1", platform="olx"))
        registry.register(StrategyTemplate(template_id="t2", name="t2", platform="instagram"))
        templates = registry.list_templates()
        assert len(templates) >= 2

    def test_clone(self, registry):
        t = StrategyTemplate(template_id="orig", name="original", platform="olx")
        registry.register(t)
        cloned = registry.clone("orig", name="copy")
        assert cloned is not None

    def test_validate(self, registry):
        t = StrategyTemplate(template_id="t1", name="t1", platform="olx")
        result = registry.validate(t)
        assert isinstance(result, list)

    def test_stats(self, registry):
        s = registry.stats()
        assert isinstance(s, dict)
