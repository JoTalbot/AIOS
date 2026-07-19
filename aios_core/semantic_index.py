"""
AIOS Semantic Index Layer v2.1.1

Provides semantic indexing and retrieval support.
"""


class SemanticIndex:
    def __init__(self):
        self.index = {}

    def add(self, key: str, value: dict):
        self.index[key] = value
        return value

    def get(self, key: str):
        return self.index.get(key)
