"""AIOS v20 Octopus Bridge.

Controlled integration point between governance kernel and execution runtime.
"""


class OctopusBridge:
    def __init__(self, runtime=None):
        self.runtime = runtime

    def execute(self, request):
        if self.runtime is None:
            return {"status": "REJECTED", "reason": "runtime_unavailable"}

        return self.runtime.execute(request)
