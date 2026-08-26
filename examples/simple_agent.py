"""Minimal AIOS agent example."""

class ExampleAgent:
    name = "example"

    async def execute(self, task):
        return {"result": task}
