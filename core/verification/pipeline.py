class ContinuousImprovementPipeline:

    def __init__(self, validator):
        self.validator = validator

    async def execute(self, state):
        result = self.validator.validate(state)
        return {
            "accepted": result.valid,
            "details": result.details
        }
