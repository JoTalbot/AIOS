class ReflectionEngine:
    def __init__(self, memory):
        self.memory = memory

    async def review(self, task_result):
        reflection = {
            "success": True,
            "lessons": [],
            "result": task_result
        }

        if self.memory:
            self.memory.store(reflection)

        return reflection
