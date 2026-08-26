"""AIOS API server foundation."""

from .endpoint import invoke


class APIServer:
    def __init__(self, pipeline=None):
        self.pipeline = pipeline

    def handle(self, request):
        return invoke(request, self.pipeline)
