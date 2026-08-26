"""AIOS long term memory storage base."""
class LongTermMemory:
    def __init__(self):
        self.storage = {}
    def save(self,key,value):
        self.storage[key]=value
    def get(self,key):
        return self.storage.get(key)
