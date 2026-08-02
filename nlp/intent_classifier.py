class IntentClassifier:
    """AIOS intent classification foundation."""

    def classify(self, text):
        return {
            "text": text,
            "intent": None
        }
