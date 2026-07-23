"""Tests for AIOS SDK client (unit tests — no server needed)."""
from sdk.aios_sdk import AIOSClient, AIOSClientSync


def test_client_creation():
    c = AIOSClient("http://localhost:8000", api_key="test-key")
    assert c.base_url == "http://localhost:8000"
    assert "Bearer test-key" in c.headers["Authorization"]


def test_client_no_auth():
    c = AIOSClient("http://localhost:8000")
    assert "Authorization" not in c.headers


def test_url_builder():
    c = AIOSClient("http://localhost:8000/")
    assert c._url("/api/v1/stats") == "http://localhost:8000/api/v1/stats"


def test_sync_client_creation():
    c = AIOSClientSync("http://localhost:8000")
    assert c.base_url == "http://localhost:8000"


def test_client_default_timeout():
    c = AIOSClient("http://localhost:8000")
    assert c.timeout == 30.0


def test_client_custom_timeout():
    c = AIOSClient("http://localhost:8000", timeout=60.0)
    assert c.timeout == 60.0
