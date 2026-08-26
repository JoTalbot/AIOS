"""Automatic tool registration foundation."""

class AutoToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, tool):
        self.tools[tool.name] = tool

    def resolve(self, name):
        return self.tools.get(name)
