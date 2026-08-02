class FaultDetector:
    """AIOS fault detection foundation."""

    def detect(self, system):
        return {
            "system": system,
            "fault": False
        }
