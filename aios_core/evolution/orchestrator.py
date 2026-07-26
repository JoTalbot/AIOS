
from .template_evolution import template_evolution
from .intent_discovery import intent_discovery
from .self_healing import self_healing
import datetime

class EvolutionOrchestrator:
    def __init__(self):
        self.log = []
    
    async def run_cycle(self):
        results = {"timestamp": datetime.datetime.utcnow().isoformat()}
        try:
            results["evolved"] = await template_evolution.auto_evolve_all() if hasattr(template_evolution, "auto_evolve_all") else []
        except Exception as e:
            results["error"] = str(e)
        self.log.append(results)
        return results

evolution_orchestrator = EvolutionOrchestrator()
