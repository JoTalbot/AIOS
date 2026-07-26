
from .template_evolution import template_evolution
from .intent_discovery import intent_discovery
from .self_healing import self_healing
import datetime
from aios_core.observability.evolution_metrics import record_cycle, record_promotion, record_new_intent, record_self_heal
from aios_core.evolution.notifications import notify_template_promoted, notify_new_intent, notify_self_heal

class EvolutionOrchestrator:
    def __init__(self):
        self.log = []
    
    async def run_cycle(self):
        results = {"timestamp": datetime.datetime.utcnow().isoformat()}
        try:
            results["evolved"] = await template_evolution.auto_evolve_all() if hasattr(template_evolution, "auto_evolve_all") else []
        except Exception as e:
            results["error"] = str(e)
        record_cycle()
        for evo in results.get('evolved', []):
            record_promotion(evo.get('template_id', 'unknown'))
            await notify_template_promoted(evo.get('template_id', ''), evo.get('old_version', 0), evo.get('new_version', 1))
        self.log.append(results)
        return results

evolution_orchestrator = EvolutionOrchestrator()
