class AccessController:
    """AIOS access control foundation."""

    def allow(self, subject, resource):
        return {
            "subject": subject,
            "resource": resource,
            "allowed": True
        }
