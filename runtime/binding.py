"""Runtime binding foundation for agents, tools and memory."""

class RuntimeBinding:
    def __init__(self):
        self.bindings = {}

    def bind(self, key, value):
        self.bindings[key] = value
