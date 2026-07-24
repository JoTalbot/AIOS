"""Tests for aios_core/api_gateway.py"""
from __future__ import annotations
import pytest
from aios_core.api_gateway import APIGateway


@pytest.fixture()
def gw():
    return APIGateway()


class TestAPIGateway:
    def test_create(self, gw):
        assert gw is not None

    def test_register(self, gw):
        gw.register(path="/api/v1/test", handler=lambda req: "ok", methods=["GET"])

    def test_unregister(self, gw):
        gw.register(path="/temp", handler=lambda req: "ok", methods=["GET"])
        gw.unregister("/temp")

    def test_add_middleware(self, gw):
        gw.add_middleware(lambda req, next_fn: next_fn(req))

    def test_remove_middleware(self, gw):
        mw = lambda req, next_fn: next_fn(req)
        gw.add_middleware(mw)
        gw.remove_middleware(mw)

    def test_handle(self, gw):
        gw.register(path="/hello", handler=lambda req: "world", methods=["GET"])
        result = gw.handle(path="/hello", request={"method": "GET"})
        assert result is not None

    def test_reset_rate_limit(self, gw):
        gw.reset_rate_limit()

    def test_health(self, gw):
        h = gw.health()
        assert isinstance(h, dict)

    def test_metrics(self, gw):
        m = gw.metrics()
        assert isinstance(m, dict)

    def test_stats(self, gw):
        s = gw.stats()
        assert isinstance(s, dict)
