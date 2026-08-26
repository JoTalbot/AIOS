class MeshLoadBalancer:

    def select(self, agents):
        if not agents:
            return None

        return min(
            agents,
            key=lambda agent: getattr(agent, "load", 0)
        )
