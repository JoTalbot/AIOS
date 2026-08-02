class RestartManager:
    """Service restart management foundation."""

    def restart(self, service):
        return {
            "service": service,
            "status": "restarted"
        }
