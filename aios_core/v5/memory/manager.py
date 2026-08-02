class MemoryManager:
    """Unified memory access layer for AIOS agents."""

    def __init__(self, short_term=None, long_term=None, vector_store=None, retriever=None, embeddings=None):
        self.short_term = short_term
        self.long_term = long_term
        self.vector_store = vector_store
        self.retriever = retriever
        self.embeddings = embeddings

    def remember(self, item):
        if self.short_term:
            self.short_term.remember(item)

        vector = self.embeddings.encode(str(item)) if self.embeddings else []
        if self.vector_store:
            self.vector_store.add(vector, item)

        return item

    def recall(self, query):
        memories = self.vector_store.all() if self.vector_store else []
        if self.retriever:
            return self.retriever.search(query, memories)
        return memories

    def store(self, key, value):
        if self.long_term:
            self.long_term.save(key, value)
