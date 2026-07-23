"""Integration: Storage + Evolution cross-module."""
from aios_core.storage import Database
from aios_core.evolution_manager import EvolutionManager
def test_storage_evolution():
    db = Database(":memory:")
    em = EvolutionManager()
    assert db.stats() is not None
    assert em.stats() is not None
