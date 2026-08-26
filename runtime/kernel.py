"""AIOS Runtime Kernel foundation.

Coordinates runtime lifecycle and execution components.
"""

class RuntimeKernel:
    def __init__(self, runtime=None):
        self.runtime = runtime
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False
