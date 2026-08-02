class OLXController:
    """OLX Android automation controller foundation."""

    def __init__(self, connector=None):
        self.connector = connector

    def open_app(self):
        return {
            "action": "open_olx",
            "connected": self.connector is not None,
        }

    def execute(self, action):
        return {
            "action": action,
            "status": "queued"
        }
