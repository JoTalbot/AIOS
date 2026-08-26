class RequestPipeline:
    def __init__(self, gateway=None, runtime=None):
        self.gateway = gateway
        self.runtime = runtime

    def execute(self, request):
        if self.runtime:
            return self.runtime.execute(request)
        return request
