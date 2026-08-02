class Sandbox:
    """Secure execution sandbox foundation."""

    def __init__(self):
        self.active = False

    def start(self):
        self.active = True

    def stop(self):
        self.active = False
