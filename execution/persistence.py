"""Execution persistence boundary with idempotent result operations."""


class ExecutionStore:
    def __init__(self):
        self._states = {}

    def save(self, key, value):
        self._states[key] = value
        return value

    def load(self, key):
        return self._states.get(key)

    def delete(self, key):
        return self._states.pop(key, None)

    def save_result(self, task_id, result):
        return self.save(task_id, {"status": "completed", "result": result})

    def load_result(self, task_id):
        state = self.load(task_id)
        if not isinstance(state, dict) or state.get("status") != "completed":
            return None
        return state.get("result")
