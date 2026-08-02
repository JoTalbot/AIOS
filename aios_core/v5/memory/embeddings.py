class EmbeddingProvider:
    """Embedding generation foundation."""

    def encode(self, text):
        return {
            "text": text,
            "vector": []
        }
