class ApprovalGate:
    def __init__(self, required=False):
        self.required = required

    def check(self, proposal):
        return not self.required
