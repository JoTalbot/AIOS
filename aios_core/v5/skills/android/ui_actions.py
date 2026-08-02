class UIActions:
    """Android UI interaction adapter foundation."""

    def tap(self, x, y):
        return {"action": "tap", "x": x, "y": y}

    def swipe(self, start, end):
        return {"action": "swipe", "start": start, "end": end}

    def input_text(self, text):
        return {"action": "input_text", "text": text}

    def back(self):
        return {"action": "back"}
