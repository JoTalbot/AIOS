"""Dynamic agent creation for AIOS."""


class AgentFactory:
    def __init__(self):
        self.registry = {}

    def register_type(self, name, agent_class):
        self.registry[name] = agent_class

    def create(self, name, *args, **kwargs):
        agent = self.registry.get(name)
        if agent is None:
            raise ValueError(f"Unknown agent type: {name}")
        return agent(*args, **kwargs)
