"""Evolution manager full."""
from aios_core.evolution_manager import EvolutionManager
def test_em(): assert EvolutionManager().stats() is not None
