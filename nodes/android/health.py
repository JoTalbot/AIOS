class AndroidNodeHealth:
    """Android node health monitoring foundation."""

    def check(self, connector):
        return {
            "connected": connector.connected
        }
