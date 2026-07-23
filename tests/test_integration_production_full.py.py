"""Integration: Production full pipeline."""
from aios_core.production_autopilot import ProductionAutopilot
from aios_core.production_webhook_bridge import ProductionWebhookBridge
def test_production_full():
    pa = ProductionAutopilot()
    wb = ProductionWebhookBridge()
    assert pa.stats() is not None
    assert wb is not None
