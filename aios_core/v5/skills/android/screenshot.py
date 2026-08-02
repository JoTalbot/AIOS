class ScreenshotCapture:
    """Android screenshot capture adapter foundation."""

    def __init__(self):
        self.last_capture = None

    def capture(self):
        self.last_capture = "screenshot_placeholder"
        return self.last_capture

    def status(self):
        return {"available": self.last_capture is not None}
