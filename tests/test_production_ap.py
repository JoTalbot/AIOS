"""Tests for production autopilot and webhook bridge."""

from aios_core.production_autopilot import ProductionAutopilot
from aios_core.production_webhook_bridge import WebhookBridge


def test_autopilot_init():
    ap = ProductionAutopilot()
    assert ap is not None


def test_webhook_bridge_init():
    wb = WebhookBridge()
    assert wb is not None
