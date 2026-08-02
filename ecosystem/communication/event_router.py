class EventRouter:
    """Agent event routing foundation."""

    def route(self, event, target):
        return {
            "event": event,
            "target": target
        }
