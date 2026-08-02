class DistributedTracer:
    """Federation request tracing foundation."""

    def __init__(self):
        self.spans = []

    def trace(self, span):
        self.spans.append(span)

    def get_spans(self):
        return self.spans
