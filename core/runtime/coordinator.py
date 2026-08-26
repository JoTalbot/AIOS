"""Runtime coordinator foundation for AIOS.

Coordinates booted runtime services and execution flow.
"""


class RuntimeCoordinator:
    def __init__(self, runtime=None):
        self.runtime = runtime

    def execute(self, request):
        if self.runtime is None:
            raise RuntimeError("Runtime is not configured")
        return self.runtime.execute(request)
