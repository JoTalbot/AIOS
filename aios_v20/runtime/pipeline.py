class ExecutionPipeline:
    """Connects governance stages with runtime execution."""

    def __init__(self, gateway, executor, audit):
        self.gateway = gateway
        self.executor = executor
        self.audit = audit

    def run(self, request):
        decision = self.gateway.process(request)

        if not decision.allowed:
            self.audit.record(request, "DENIED")
            return decision

        result = self.executor.execute(request)
        self.audit.record(request, result.status)
        return result
