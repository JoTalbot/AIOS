from ..base import Agent


class OLXAgent(Agent):
    name = "olx_agent"

    def __init__(self, android_skill=None, memory=None):
        self.android_skill = android_skill
        self.memory = memory

    async def execute(self, task):
        action = task.get("action") if isinstance(task, dict) else None

        result = {
            "agent": self.name,
            "action": action,
            "status": "planned"
        }

        if self.memory:
            self.memory.remember(result)

        return result
