class WorkflowEngine:
    """Multi-step workflow execution foundation."""

    async def run(self, steps, context=None):
        results = []
        for step in steps:
            result = await step(context)
            results.append(result)
        return results
