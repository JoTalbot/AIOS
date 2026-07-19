"""AIOS Anomaly Detector"""

class AnomalyDetector:
    def __init__(self):
        self.events = []

    def detect(self, event):
        self.events.append(event)
        return False

    def history(self):
        return self.events
