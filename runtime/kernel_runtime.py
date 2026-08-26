class KernelRuntime:
    def __init__(self, scheduler, memory, bus, llm, tools):
        self.scheduler = scheduler
        self.memory = memory
        self.bus = bus
        self.llm = llm
        self.tools = tools
        self.running = False

    async def boot(self):
        self.running = True
        worker = self.scheduler.worker()
        return worker

    def status(self):
        return {
            "running": self.running,
            "components": [
                "scheduler",
                "memory",
                "communication",
                "llm",
                "tools"
            ]
        }
