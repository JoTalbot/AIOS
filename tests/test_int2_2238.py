"""Integration2 test 2238."""
from aios_core.orchestrator import Orchestrator
from aios_core.planner import Planner
from aios_core.capability_engine import CapabilityEngine
from aios_core.constitution_engine import ConstitutionEngine
from aios_core.ai_ethics import AIEthicsFramework

def test():
    for o in [Orchestrator(),Planner(),CapabilityEngine(),ConstitutionEngine(),AIEthicsFramework()]:
        assert o.stats() is not None
