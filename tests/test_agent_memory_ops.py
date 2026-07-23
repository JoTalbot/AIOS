from aios_core.agent_architecture import AgentMemory, AdvancedAgent
def test_memory():
    a = AdvancedAgent('test')
    a.memory.short_term.append({'msg': 'hello'})
    assert a.stats()['memory_items'] == 1