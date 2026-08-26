class AuditMemorySync:
    def __init__(self, memory):
        self.memory = memory

    def record(self, event):
        self.memory.store(event)
