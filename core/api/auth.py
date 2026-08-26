"""Authentication middleware foundation for AIOS API."""

class AuthMiddleware:
    def __init__(self, validator=None):
        self.validator = validator

    def check(self, request):
        if self.validator:
            return self.validator(request)
        return True
