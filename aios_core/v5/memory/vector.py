class VectorMemory:
    def __init__(self):
        self.vectors = []

    def add(self, vector, metadata=None):
        self.vectors.append({
            "vector": vector,
            "metadata": metadata or {}
        })

    def search(self, query):
        return self.vectors
