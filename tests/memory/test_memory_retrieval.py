from core.memory.agent_memory_v2 import AgentMemoryV2
from core.memory.memory_policy_integration import MemoryPolicyIntegration


def test_memory_store_and_retrieve():
    memory = AgentMemoryV2()
    memory.store("task_success", {"reward": 1.0})

    result = memory.retrieve("task_success")

    assert result is not None
    assert result.value["reward"] == 1.0


def test_memory_policy_context():
    memory = AgentMemoryV2()
    memory.store("decision", {"action": "execute"})

    bridge = MemoryPolicyIntegration(memory)
    context = bridge.get_context("decision")

    assert context is not None
    assert context.value["action"] == "execute"
