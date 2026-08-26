class ResponseLayer:
    def build(self, result, context=None):
        return {
            "result": result,
            "request_id": getattr(context, "request_id", None),
        }
