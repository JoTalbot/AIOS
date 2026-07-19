"""AIOS Data Manager"""

class DataManager:
    def __init__(self):
        self.storage = {}

    def put(self, key, value):
        self.storage[key] = value
        return True

    def get(self, key):
        return self.storage.get(key)
