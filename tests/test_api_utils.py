"""Tests for API errors, examples, and enhanced API."""

from aios_core.api.errors import RequestSafetyMiddleware
from aios_core.api.example import create_example_app


def test_request_safety_middleware():
    mw = RequestSafetyMiddleware(None)
    assert mw.max_body_bytes == 1_048_576


def test_create_example_app():
    app = create_example_app()
    assert app is not None
