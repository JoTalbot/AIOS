"""AIOS autonomous execution demo entrypoint."""


async def run_demo(runtime, goal):
    result = await runtime.run(goal)
    return result
