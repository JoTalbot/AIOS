"""Smoke test — verify all major imports resolve."""
import importlib

MODULES = [
    "aios_core", "aios_core.storage", "aios_core.orchestrator",
    "aios_core.planner", "aios_core.knowledge_graph", "aios_core.memory_manager",
    "aios_core.event_bus", "aios_core.constitution_engine", "aios_core.config",
    "aios_core.rate_limiter", "aios_core.circuit_breaker", "aios_core.self_healing",
    "aios_core.benchmark", "aios_core.diffusion", "aios_core.active_learning",
    "aios_core.ai_advisor", "aios_core.ai_ethics", "aios_core.ai_engineer",
    "aios_core.ai_product_manager", "aios_core.ai_researcher",
]

def test_all_imports():
    for mod in MODULES:
        importlib.import_module(mod)
