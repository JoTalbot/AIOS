class GlobalSecurity:
    """Planetary security foundation."""

    def verify(self, request):
        return {
            "request": request,
            "verified": True
        }
