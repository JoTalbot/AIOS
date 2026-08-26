class FederationSync:
    def __init__(self):
        self.history = []

    def sync(self, update):
        self.history.append(update)
        return True
