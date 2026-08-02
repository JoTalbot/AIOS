class RoutingProtocol:
    """Planetary message routing foundation."""

    def route(self, source, target, message):
        return {
            "source": source,
            "target": target,
            "message": message
        }
