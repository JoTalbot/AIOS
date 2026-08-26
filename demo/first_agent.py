import asyncio


class DemoAgent:
    def __init__(self, runtime):
        self.runtime = runtime

    async def execute(self, goal):
        plan = ["analyze", "act", "remember", "reflect"]
        return {
            "goal": goal,
            "plan": plan,
            "status": "completed"
        }


async def main():
    agent = DemoAgent(None)
    result = await agent.execute("Build AIOS component")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
