class ExecutionGuard:
    def __init__(self, security_layer=None):
        self.security_layer = security_layer

    def check(self, action):
        return True

    def execute_allowed(self, action):
        return self.check(action)
