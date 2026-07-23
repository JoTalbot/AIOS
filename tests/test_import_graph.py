"""Tests verifying important module imports resolve correctly."""

import importlib


def test_core_imports():
    modules = [
        "aios_core",
        "aios_core.storage",
        "aios_core.orchestrator",
        "aios_core.planner",
        "aios_core.knowledge_graph",
        "aios_core.memory_manager",
        "aios_core.self_healing",
        "aios_core.rate_limiter",
        "aios_core.event_bus",
        "aios_core.constitution_engine",
    ]
    for mod in modules:
        importlib.import_module(mod)
