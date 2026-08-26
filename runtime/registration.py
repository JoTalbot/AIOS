"""Automatic component registration foundation."""


class ComponentRegistry:
    def __init__(self):
        self.components = {}

    def register(self, name, component):
        self.components[name] = component
