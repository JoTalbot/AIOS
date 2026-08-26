class AgentRunner:
    """Runs agent execution sessions."""

    def __init__(self, execution_manager=None):
        self.execution_manager = execution_manager

    def run(self, agent, request):
        return agent.execute(request)
