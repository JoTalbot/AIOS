class SafetyConstraintSystem:

    def __init__(self):
        self.constraints = []

    def add(self, constraint):
        self.constraints.append(constraint)

    def validate(self, context):
        return all(
            constraint(context)
            for constraint in self.constraints
        )
