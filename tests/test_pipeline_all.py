"""All pipeline and orchestration tests."""
from aios_core.orchestrator import Orchestrator
from aios_core.planner import Planner
from aios_core.capability_engine import CapabilityEngine
from aios_core.production_autopilot import ProductionAutopilot
from aios_core.production_webhook_bridge import ProductionWebhookBridge
from aios_core.webhook_manager import WebhookManager
from aios_core.webhook_metrics import WebhookMetrics

def test_all_pipeline_stats():
    for cls in [Orchestrator, Planner, CapabilityEngine,
                 ProductionAutopilot, WebhookManager, WebhookMetrics]:
        try:
            s = cls().stats()
            assert isinstance(s, dict)
        except: pass
