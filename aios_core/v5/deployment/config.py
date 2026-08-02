class DeploymentConfig:
    """Production deployment configuration foundation."""

    def __init__(self, environment="development"):
        self.environment = environment

    def get(self):
        return {
            "environment": self.environment
        }
