"""AIOS v25.3 Long Term Autonomous Memory."""
class AutonomousMemory:
    def __init__(self): self.memory=[]
    def remember(self,item): self.memory.append(item)
    def recall(self): return self.memory
