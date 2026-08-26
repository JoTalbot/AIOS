"""AIOS v23.3 Multi Agent Coordination Layer.

Provides the foundation for communication and coordination between
independent cognitive agents.
"""


class AgentMessage:
    def __init__(self, sender, receiver, payload):
        self.sender = sender
        self.receiver = receiver
        self.payload = payload


class MultiAgentCoordinator:
    def __init__(self):
        self.agents = {}
        self.messages = []

    def register_agent(self, agent_id, agent):
        self.agents[agent_id] = agent

    def send_message(self, sender, receiver, payload):
        message = AgentMessage(sender, receiver, payload)
        self.messages.append(message)
        return message

    def list_agents(self):
        return list(self.agents.keys())
