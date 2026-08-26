"""AIOS v24.1 Dynamic Agent Role Adaptation Engine."""


class RoleAdaptationEngine:
    def __init__(self):
        self.roles = {}

    def assign_role(self, agent_id, role):
        self.roles[agent_id] = role
        return role

    def get_role(self, agent_id):
        return self.roles.get(agent_id)

    def adapt_role(self, agent_id, performance_signal):
        role = self.roles.get(agent_id, "observer")
        if performance_signal == "high":
            role = "coordinator"
        elif performance_signal == "low":
            role = "learner"
        self.roles[agent_id] = role
        return role
