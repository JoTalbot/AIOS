"""Critic agent for AIOS decision evaluation."""


class CriticAgent:
    def __init__(self, name="critic"):
        self.name = name

    def evaluate(self, decision):
        return {"decision": decision, "approved": True}
