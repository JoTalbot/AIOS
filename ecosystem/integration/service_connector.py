class ServiceConnector:
    """External service connection foundation."""

    def connect(self, service):
        return {
            "service": service,
            "connected": True
        }
