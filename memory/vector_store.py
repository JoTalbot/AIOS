class VectorMemory:
    def __init__(self):
        self.entries = []

    def add(self, text, metadata=None):
        self.entries.append({
            'text': text,
            'metadata': metadata or {}
        })

    def search(self, query):
        return [item for item in self.entries if query.lower() in item['text'].lower()]
