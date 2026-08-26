class WorkflowStep:
    def __init__(self, role, task):
        self.role = role
        self.task = task


class AgentWorkflow:
    def __init__(self, router=None, bus=None):
        self.router = router
        self.bus = bus

    def execute(self, steps):
        results = []
        for step in steps:
            agent = None
            if self.router:
                agent = self.router.route(step.role)
            results.append({
                "role": step.role,
                "task": step.task,
                "agent": agent,
            })
        return results
