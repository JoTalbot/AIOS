class GovernanceValidator:
    def __init__(self, constitution):
        self.constitution = constitution

    def validate(self, action: str) -> bool:
        return self.constitution.check(action)
