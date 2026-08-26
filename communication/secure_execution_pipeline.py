class SecureExecutionPipeline:
    def __init__(self, protocol, guard, trust_manager):
        self.protocol = protocol
        self.guard = guard
        self.trust_manager = trust_manager

    def execute(self, agent, action):
        if not self.trust_manager.check(agent):
            return False
        return self.guard.allow(action)
