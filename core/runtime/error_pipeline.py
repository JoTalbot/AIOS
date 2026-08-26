"""Runtime error pipeline foundation."""

class ErrorPipeline:
    def handle(self, error):
        return {"error": str(error)}
