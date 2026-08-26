class HealthMonitor:
    def check(self, components=None):
        return {"status": "ok", "components": components or {}}
