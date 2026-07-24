"""Tests for aios_core/external_integration.py"""
from __future__ import annotations
import pytest
from aios_core.external_integration import ExternalIntegrationAPI, IntegrationMetrics


class TestIntegrationMetrics:
    def test_create(self):
        m = IntegrationMetrics()
        assert m is not None

    def test_record_webhook_success(self):
        m = IntegrationMetrics()
        m.record_webhook_success()

    def test_record_webhook_failure(self):
        m = IntegrationMetrics()
        m.record_webhook_failure()

    def test_record_graphql_request(self):
        m = IntegrationMetrics()
        m.record_graphql_request()

    def test_record_latency(self):
        m = IntegrationMetrics()
        m.record_latency(duration_ms=150.0)


class TestExternalIntegrationAPI:
    def test_create(self):
        api = ExternalIntegrationAPI()
        assert api is not None

    def test_add_webhook(self):
        api = ExternalIntegrationAPI()
        api.add_webhook(name="test_hook", config={"url": "https://example.com/hook", "events": ["test"]})

    def test_set_graphql(self):
        api = ExternalIntegrationAPI()
        api.set_graphql(config={"endpoint": "https://example.com/graphql"})
