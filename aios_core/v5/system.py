from .config import AIOSConfig
from .kernel.lifecycle import LifecycleManager
from .agents.registry import AgentRegistry
from .security.audit import AuditLog
from .memory.manager import MemoryManager


class AIOSSystem:
    def __init__(self, memory: MemoryManager | None = None):
        self.config = AIOSConfig()
        self.lifecycle = LifecycleManager()
        self.agents = AgentRegistry()
        self.audit = AuditLog()
        self.memory = memory

    def start(self):
        self.lifecycle.start()

    def status(self):
        return {
            "version": self.config.version,
            "state": self.lifecycle.state.value,
            "agents": self.agents.list_agents(),
        }
