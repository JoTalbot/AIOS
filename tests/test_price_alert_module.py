"""Tests for aios_core/price_alert_system.py"""
from __future__ import annotations
import pytest
from aios_core.price_alert_system import PriceAlertSystem, PriceAlert, AlertCondition


@pytest.fixture()
def system():
    return PriceAlertSystem(default_cooldown=60, max_alerts=100)


class TestPriceAlert:
    def test_create(self):
        a = PriceAlert(alert_id="a1", rule_id="r1", platform="olx", fingerprint="fp1",
                       title="iPhone", condition=AlertCondition.BELOW_THRESHOLD)
        assert a.alert_id == "a1"

    def test_age_minutes_is_property(self):
        a = PriceAlert(alert_id="a1", rule_id="r1", platform="olx", fingerprint="fp1",
                       title="t", condition=AlertCondition.PRICE_DROP_PCT)
        assert isinstance(a.age_minutes, (int, float))

    def test_to_dict(self):
        a = PriceAlert(alert_id="a1", rule_id="r1", platform="olx", fingerprint="fp1",
                       title="t", condition=AlertCondition.PRICE_DROP_PCT)
        d = a.to_dict()
        assert isinstance(d, dict)


class TestPriceAlertSystem:
    def test_create(self):
        s = PriceAlertSystem()
        assert s is not None

    def test_create_rule(self, system):
        rule = system.create_rule(name="r1", platform="olx", fingerprint="fp1",
                                  condition=AlertCondition.BELOW_THRESHOLD, threshold=500)
        assert rule is not None

    def test_get_alerts(self, system):
        alerts = system.get_alerts()
        assert isinstance(alerts, list)

    def test_acknowledge(self, system):
        system.acknowledge("alert_1")

    def test_stats(self, system):
        s = system.stats()
        assert isinstance(s, dict)
