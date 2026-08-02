from aios_core.v5.memory.context import AgentContext


def test_memory_context_flow():
    context = AgentContext(task="analyze market")
    context.add_memory({"key": "price_history"})
    context.add_decision({"action": "review"})

    assert len(context.memories) == 1
    assert len(context.decisions) == 1
