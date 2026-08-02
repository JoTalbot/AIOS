class AppController:
    """Android application control adapter foundation."""

    def __init__(self, bridge=None):
        self.bridge = bridge

    def open_app(self, package_name: str):
        return {
            "package": package_name,
            "status": "requested"
        }
