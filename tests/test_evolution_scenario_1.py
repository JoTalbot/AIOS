from aios_core.evolution_manager import EvolutionManager
def test(): s = EvolutionManager().stats(); assert isinstance(s, dict)
