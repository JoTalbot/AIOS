"""V-test 2821."""
from aios_core.orchestrator import Orchestrator
from aios_core.planner import Planner
from aios_core.capability_engine import CapabilityEngine
from aios_core.constitution_engine import ConstitutionEngine
from aios_core.ai_ethics import AIEthicsFramework
from aios_core.ai_advisor import AISalesAdvisor
from aios_core.model_registry import ModelRegistry

def test():
    for o in [Orchestrator(),Planner(),CapabilityEngine(),ConstitutionEngine(),AIEthicsFramework(),ModelRegistry()]:
        s = o.stats()
        assert s is not None
