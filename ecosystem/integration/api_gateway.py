class APIGateway:
    """External API gateway integration foundation."""

    def request(self, service, payload):
        return {
            "service": service,
            "payload": payload
        }
