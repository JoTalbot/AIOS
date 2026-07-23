"""Evolution pipeline."""
from aios_core.evolution_manager import EvolutionManager
from aios_core.autonomy_manager import AutonomyManager

def test_evolution_flow():
    em = EvolutionManager()
    am = AutonomyManager()
    assert em.stats() is not None
    assert am.stats() is not None
