"""HTTP channel adapter foundation for AIOS."""

class HTTPChannel:
    async def receive(self, request):
        return request

    async def send(self, response):
        return response
