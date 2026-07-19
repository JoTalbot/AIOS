"""
AIOS Connector Manager Layer v2.1.1

Manages external connectors and integrations.
"""


class ConnectorManager:
    def __init__(self):
        self.connectors = {}

    def register(self, name: str, connector: dict):
        self.connectors[name] = connector
        return connector

    def get(self, name: str):
        return self.connectors.get(name)
