"""
AIOS Lifecycle Manager Layer v2.1.1

Manages component lifecycle states.
"""


class LifecycleManager:
    def __init__(self):
        self.components = {}

    def set_state(self, component: str, state: str):
        self.components[component] = state
        return {"component": component, "state": state}

    def get_state(self, component: str):
        return self.components.get(component)
