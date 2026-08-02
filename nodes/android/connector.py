class AndroidConnector:
    """Android device communication foundation."""

    def __init__(self, device_id=None):
        self.device_id = device_id
        self.connected = False

    def connect(self):
        self.connected = True
        return self.connected

    def status(self):
        return {
            "device": self.device_id,
            "connected": self.connected,
        }
