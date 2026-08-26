class ExecutionEngine:
    def __init__(self, planner, tools, memory, reflection):
        self.planner = planner
        self.tools = tools
        self.memory = memory
        self.reflection = reflection

    async def execute(self, agent, goal):
        plan = await self.planner.create_plan(goal)
        results = []

        for step in plan:
            result = await self.tools.run(step)
            results.append(result)
            self.memory.remember(agent, result)

        review = await self.reflection.evaluate(results)

        return {
            "goal": goal,
            "results": results,
            "reflection": review
        }
