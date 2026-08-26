class GovernanceGateway:
    def __init__(self, policy_engine, access_control, threat_detector):
        self.policy_engine = policy_engine
        self.access_control = access_control
        self.threat_detector = threat_detector

    def authorize(self, request):
        threat = self.threat_detector.analyze(request)
        if threat.level == "critical":
            return False

        return self.access_control.check(
            request.capability,
            request.scope
        )
