class AndroidBridge:
    """Adapter interface for Android automation backends."""

    def __init__(self):
        self.connected = False

    def connect(self):
        self.connected = True

    def status(self):
        return {"connected": self.connected}
