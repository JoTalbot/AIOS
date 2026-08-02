class AIOSDashboard:
    """AIOS monitoring dashboard foundation."""

    def __init__(self, runtime=None):
        self.runtime = runtime

    def status(self):
        return {
            "dashboard": "active",
            "runtime": self.runtime is not None,
        }
