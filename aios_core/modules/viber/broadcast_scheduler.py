"""Viber broadcast scheduler — inherits WhatsApp BroadcastScheduler for Viber platform."""

from aios_core.modules.whatsapp.broadcast_scheduler import (
    BroadcastScheduler,
)


class ViberBroadcastScheduler(BroadcastScheduler):
    """Broadcast scheduler for Viber — same interface as WhatsApp."""
