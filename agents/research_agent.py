"""AIOS research agent foundation."""


class ResearchAgent:
    def __init__(self, name="research_agent"):
        self.name = name
        self.knowledge = []

    def add_knowledge(self, item):
        self.knowledge.append(item)

    def recall(self):
        return self.knowledge
