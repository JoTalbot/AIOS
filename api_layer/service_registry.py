class ServiceRegistry:
    """AIOS service registry foundation."""

    def register(self, service):
        return {
            "service": service,
            "registered": True
        }
