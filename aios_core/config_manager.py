"""AIOS Configuration Layer v2.1.1"""

class ConfigManager:
    def __init__(self):
        self.config = {}

    def set(self, key, value):
        self.config[key] = value
