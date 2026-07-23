"""Tests for WebSocket support"""

from starlette.testclient import TestClient

from aios_core.api.app import create_app


def test_websocket_connection():
    app = create_app(auth_required=False)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Just verify the connection opens
        assert websocket is not None
