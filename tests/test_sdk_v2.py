"""Smoke tests for SDK v4.2.0 client."""

from sdk.aios_sdk import AiosClient


def test_client_init():
    c = AiosClient(base_url="http://localhost:8000", api_key="test-key")
    assert c is not None
    assert c.base_url == "http://localhost:8000"
