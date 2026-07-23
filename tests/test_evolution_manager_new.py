"""evolution_manager test."""
def test(): from aios_core.evolution_manager import EvolutionManager; s = EvolutionManager().stats(); assert isinstance(s, dict)
