"""Exceptions raised at the AIOS v20 kernel boundary."""


class KernelError(Exception):
    """Base class for kernel boundary errors."""


class PermissionDenied(KernelError):
    """Raised when an already-evaluated action is enforced as denied."""


class UnknownIdentity(PermissionDenied):
    """Raised when an unregistered agent requests kernel processing."""
