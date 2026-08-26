import asyncio


class FullAgentRun:
    def __init__(self, planner, executor, memory, reflection):
        self.planner = planner
        self.executor = executor
        self.memory = memory
        self.reflection = reflection

    async def run(self, goal):
        plan = await self.planner.create_plan(goal)
        result = await self.executor.execute(plan)
        self.memory.remember({"goal": goal, "result": result})
        review = self.reflection.analyze(result)
        return {
            "result": result,
            "reflection": review
        }
