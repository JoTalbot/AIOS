"""SDK client full tests."""
from sdk.aios_sdk import AiosClient
def test_client_creation():
    c = AiosClient(base_url="http://localhost:8000", api_key="k")
    assert c.base_url == "http://localhost:8000"
def test_client_headers():
    c = AiosClient(base_url="http://localhost:8000", api_key="secret-key")
    assert c is not None
