class MiddlewareChain:
    def __init__(self):
        self.middlewares = []

    def add(self, middleware):
        self.middlewares.append(middleware)

    def execute(self, request, handler):
        result = request
        for middleware in self.middlewares:
            result = middleware(result)
        return handler(result)
