"""Runtime metrics collector."""
class Metrics:
    def __init__(self): self.data={}
    def increment(self,name): self.data[name]=self.data.get(name,0)+1
