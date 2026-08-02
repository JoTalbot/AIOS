class AppiumController:
    """Appium automation adapter foundation."""

    def __init__(self):
        self.session_active = False

    def start_session(self):
        self.session_active = True

    def stop_session(self):
        self.session_active = False

    def status(self):
        return {"session_active": self.session_active}
