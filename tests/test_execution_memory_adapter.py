from execution.memory_adapter import ExecutionMemoryAdapter


class Memory:
    def __init__(self):
        self.items = []

    def remember(self, item, permanent=False):
        self.items.append((item, permanent))

    def recall(self, query=None):
        return [item for item, _ in self.items if query is None or query in str(item)]


def test_memory_adapter_delegates_and_recalls():
    memory = Memory()
    adapter = ExecutionMemoryAdapter(memory)
    adapter.remember({"task_id": "1"}, permanent=True)
    assert adapter.recall("task_id") == [{"task_id": "1"}]
    assert memory.items[0][1] is True


def test_memory_adapter_without_memory_is_safe():
    adapter = ExecutionMemoryAdapter()
    assert adapter.remember({"task_id": "1"}) is None
    assert adapter.recall() == []
