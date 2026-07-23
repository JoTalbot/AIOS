"""Tests for API route count and health endpoints."""

from aios_core.api.app import create_app


def test_app_creation():
    app = create_app(auth_required=False)
    assert app is not None


def test_health_endpoint_exists():
    app = create_app(auth_required=False)
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    assert any('/health' in p for p in routes)
