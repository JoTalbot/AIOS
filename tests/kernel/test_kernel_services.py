"""AIOS v20 kernel service tests."""

from aios.kernel.capability_registry import Capability, CapabilityRegistry
from aios.kernel.evolution_controller import EvolutionController
from aios.kernel.memory_fabric import MemoryFabric


def test_memory_fabric_roundtrip():
    memory = MemoryFabric()
    memory.remember("hello", "semantic")
    assert memory.recall("semantic")[0].content == "hello"


def test_capability_registry():
    registry = CapabilityRegistry()
    registry.register(Capability("search"))
    assert registry.get("search") is not None


def test_evolution_snapshot():
    controller = EvolutionController()
    controller.observe("metric")
    controller.propose("improve")
    assert controller.snapshot()["observations"] == ["metric"]
