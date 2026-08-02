class ADBClient:
    """ADB automation adapter foundation."""

    def __init__(self):
        self.connected = False

    def connect(self):
        self.connected = True
        return self.connected

    def status(self):
        return {"connected": self.connected}
