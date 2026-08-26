class AgentRuntime:
    def __init__(self, agent_id, capabilities=None):
        self.agent_id = agent_id
        self.capabilities = capabilities or []
        self.status = "initialized"

    def start(self):
        self.status = "active"

    def can_execute(self, capability):
        return capability in self.capabilities

    def stop(self):
        self.status = "stopped"
