class SelfHealing:
    def __init__(self, health_monitor, recovery_manager):
        self.health_monitor = health_monitor
        self.recovery_manager = recovery_manager

    def inspect(self):
        status = self.health_monitor.last()
        if status and status.get("status") != "ok":
            return self.recovery_manager.recover(status)
        return {"status": "healthy"}
