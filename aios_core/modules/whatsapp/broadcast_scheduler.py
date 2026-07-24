"""WhatsApp/Viber broadcast scheduler — schedule approval-gated bulk messages.

Broadcast scheduler for messenger-first platforms:
- Create broadcast groups (lists of contacts)
- Schedule messages with timing (delay, jitter, pacing)
- Compliance guard: approval-only, never auto-send
- Track delivery status per recipient
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class BroadcastStatus(Enum):
    """Status of a broadcast."""

    DRAFT = "draft"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BroadcastMessage:
    """A single broadcast message targeting multiple contacts."""

    id: str
    text: str
    contact_tags: list[str] = field(default_factory=list)
    status: BroadcastStatus = BroadcastStatus.DRAFT
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sent_count: int = 0
    total_count: int = 0
    jitter_seconds: float = 2.0
    pacing_per_hour: int = 20

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "id": self.id,
            "text": self.text,
            "contact_tags": self.contact_tags,
            "status": self.status.value,
            "created_at": self.created_at,
            "sent_count": self.sent_count,
            "total_count": self.total_count,
            "jitter_seconds": self.jitter_seconds,
            "pacing_per_hour": self.pacing_per_hour,
        }


class BroadcastScheduler:
    """Schedule and manage approval-gated broadcast messages.

    Compliance: messages are NEVER auto-sent. All broadcasts
    must be approved by a human operator before sending.
    """

    def __init__(self, storage) -> None:
        """Initialize BroadcastScheduler.

        Args:
            storage: Platform storage instance.
        """
        self.storage = storage
        self._broadcasts: dict[str, BroadcastMessage] = {}
        self._counter: int = 0

    def create_broadcast(
        self,
        text: str,
        contact_tags: list[str] | None = None,
        jitter_seconds: float = 2.0,
        pacing_per_hour: int = 20,
    ) -> BroadcastMessage:
        """Create a draft broadcast message.

        Args:
            text: Message text.
            contact_tags: Tags to filter contacts.
            jitter_seconds: Jitter between messages (human-like pacing).
            pacing_per_hour: Max messages per hour.

        Returns:
            BroadcastMessage in DRAFT status (requires approval).
        """
        now = datetime.now(timezone.utc).isoformat()
        self._counter += 1
        msg_id = f"broadcast_{self._counter}"
        broadcast = BroadcastMessage(
            id=msg_id,
            text=text,
            contact_tags=contact_tags or [],
            jitter_seconds=jitter_seconds,
            pacing_per_hour=pacing_per_hour,
        )
        self._broadcasts[msg_id] = broadcast
        return broadcast

    def approve_broadcast(self, broadcast_id: str) -> BroadcastMessage | None:
        """Approve a broadcast for sending (human operator step).

        Args:
            broadcast_id: Broadcast ID to approve.

        Returns:
            Approved BroadcastMessage or None.
        """
        broadcast = self._broadcasts.get(broadcast_id)
        if broadcast and broadcast.status == BroadcastStatus.DRAFT:
            broadcast.status = BroadcastStatus.APPROVED
        return broadcast

    def list_broadcasts(self, status: BroadcastStatus | None = None) -> list[BroadcastMessage]:
        """List all broadcasts, optionally filtered by status.

        Args:
            status: Optional status filter.

        Returns:
            List of BroadcastMessage objects.
        """
        broadcasts = list(self._broadcasts.values())
        if status:
            broadcasts = [b for b in broadcasts if b.status == status]
        return broadcasts

    def cancel_broadcast(self, broadcast_id: str) -> bool:
        """Cancel a broadcast.

        Args:
            broadcast_id: Broadcast ID to cancel.

        Returns:
            True if cancelled.
        """
        broadcast = self._broadcasts.get(broadcast_id)
        if broadcast:
            broadcast.status = BroadcastStatus.FAILED
            return True
        return False
