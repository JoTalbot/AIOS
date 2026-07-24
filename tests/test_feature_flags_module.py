"""Tests for aios_core/feature_flags.py"""
from __future__ import annotations
import pytest
from aios_core.feature_flags import FlagStore, FeatureFlags


@pytest.fixture()
def store():
    return FlagStore()


@pytest.fixture()
def flags():
    return FeatureFlags()


class TestFlagStore:
    def test_register(self, store):
        store.register("dark_mode", description="Enable dark mode")
        assert store.get_flag("dark_mode") is not None

    def test_enable(self, store):
        store.register("feature_x")
        store.enable("feature_x")
        assert store.is_enabled("feature_x") is True

    def test_disable(self, store):
        store.register("feature_y")
        store.enable("feature_y")
        store.disable("feature_y")
        assert store.is_enabled("feature_y") is False

    def test_toggle(self, store):
        store.register("toggle_me")
        store.toggle("toggle_me")
        first = store.is_enabled("toggle_me")
        store.toggle("toggle_me")
        assert store.is_enabled("toggle_me") != first

    def test_archive(self, store):
        store.register("old_feature")
        store.archive("old_feature")

    def test_list_flags(self, store):
        store.register("f1")
        store.register("f2")
        flags = store.list_flags()
        assert len(flags) >= 2

    def test_get_audit_log(self, store):
        store.register("audited")
        store.enable("audited")
        log = store.get_audit_log()
        assert isinstance(log, list)

    def test_metrics(self, store):
        store.register("metric_flag")
        m = store.metrics("metric_flag")
        assert isinstance(m, dict)

    def test_stats(self, store):
        s = store.stats()
        assert isinstance(s, dict)


class TestFeatureFlags:
    def test_enable(self, flags):
        flags.enable("new_ui")

    def test_is_enabled(self, flags):
        flags.enable("test_flag")
        assert flags.is_enabled("test_flag") is True

    def test_toggle(self, flags):
        flags.toggle("toggle_flag")

    def test_list(self, flags):
        result = flags.list()
        assert isinstance(result, (list, dict))

    def test_store(self, flags):
        assert isinstance(flags.store(), FlagStore)
