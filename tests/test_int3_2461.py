"""Integration3 2461."""
from aios_core.orchestrator import Orchestrator
from aios_core.planner import Planner
from aios_core.constitution_engine import ConstitutionEngine
from aios_core.ai_ethics import AIEthicsFramework
from aios_core.model_registry import ModelRegistry

def test():
    for o in [Orchestrator(),Planner(),ConstitutionEngine(),AIEthicsFramework(),ModelRegistry()]:
        assert o.stats() is not None
