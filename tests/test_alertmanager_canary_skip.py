"""Tests for the canary skip-when-monitoring-down behaviour."""

from __future__ import annotations

import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.alertmanager_delivery_canary as canary  # noqa: E402


def test_skip_when_alertmanager_refuses(monkeypatch):
    def boom(nonce, *, resolve=False):
        raise urllib.error.URLError(ConnectionRefusedError(111, "refused"))

    monkeypatch.setattr(canary, "_post_alert", boom)
    assert canary.main() == 0


def test_propagates_other_url_errors(monkeypatch):
    def boom(nonce, *, resolve=False):
        raise urllib.error.URLError(TimeoutError("timeout"))

    monkeypatch.setattr(canary, "_post_alert", boom)
    try:
        canary.main()
    except urllib.error.URLError:
        return
    raise AssertionError("expected URLError to propagate")
