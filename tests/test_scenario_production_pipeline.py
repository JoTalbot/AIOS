"""Production pipeline."""
from aios_core.production_autopilot import ProductionAutopilot
from aios_core.production_webhook_bridge import ProductionWebhookBridge
from aios_core.webhook_manager import WebhookManager
from aios_core.webhook_metrics import WebhookMetrics

def test_production_flow():
    pa = ProductionAutopilot()
    wb = ProductionWebhookBridge()
    wm = WebhookManager()
    wmm = WebhookMetrics()
    assert pa.stats() is not None
    assert wb is not None
    assert wm is not None
    assert wmm is not None
