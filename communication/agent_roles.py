class AgentRole:
    PLANNER = "planner"
    EXECUTOR = "executor"
    EVALUATOR = "evaluator"


class AgentTask:
    def __init__(self, task_id: str, role: str, payload=None):
        self.task_id = task_id
        self.role = role
        self.payload = payload


class AgentRoleRouter:
    def __init__(self):
        self.handlers = {}

    def register(self, role: str, agent_id: str):
        self.handlers[role] = agent_id

    def route(self, task: AgentTask):
        return self.handlers.get(task.role)
