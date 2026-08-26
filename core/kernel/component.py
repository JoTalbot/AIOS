from abc import ABC


class KernelComponent(ABC):
    """Base contract for AIOS kernel-managed components."""

    name = None
    requires = []

    def initialize(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def health(self):
        return True
