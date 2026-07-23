"""Full production module tests."""

from aios_core.production_autopilot import ProductionAutopilot
from aios_core.production_webhook_bridge import ProductionWebhookBridge
from aios_core.production_simulation_report import SimulationReport


def test_autopilot_stats():
    ap = ProductionAutopilot()
    s = ap.stats()
    assert isinstance(s, dict)


def test_webhook_bridge():
    wb = ProductionWebhookBridge()
    assert wb is not None


def test_simulation_report():
    sr = SimulationReport()
    assert sr is not None
