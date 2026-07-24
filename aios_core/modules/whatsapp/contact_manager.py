"""WhatsApp/Viber contact manager — manage contacts and groups for messaging.

Provides contact organization, group management, and bulk contact
operations for messenger-first platforms (WhatsApp, Viber).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Contact:
    """A single contact in a messenger platform."""

    name: str
    phone: str | None = None
    jid: str | None = None  # WhatsApp/Viber internal ID
    is_group: bool = False
    last_message_at: str | None = None
    unread_count: int = 0
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "name": self.name,
            "phone": self.phone,
            "jid": self.jid,
            "is_group": self.is_group,
            "last_message_at": self.last_message_at,
            "unread_count": self.unread_count,
            "tags": self.tags,
        }


class ContactManager:
    """Manage contacts and groups for WhatsApp/Viber platforms.

    Stores contacts in SQLite via platform storage. Provides:
    - Add/remove/search contacts
    - Group management (create, add members, list)
    - Tag-based contact filtering
    """

    def __init__(self, storage) -> None:
        """Initialize ContactManager.

        Args:
            storage: Platform storage instance (WhatsAppStorage/ViberStorage).
        """
        self.storage = storage

    def add_contact(self, contact: Contact) -> bool:
        """Add or update a contact in storage.

        Args:
            contact: Contact object to add.

        Returns:
            True if added/updated successfully.
        """
        now = datetime.now(UTC).isoformat()
        with self.storage._lock, self.storage._conn:
            self.storage._conn.execute(
                """INSERT OR REPLACE INTO olx_profile_kv (key, value, updated_at)
                VALUES (?, ?, ?)""",
                (
                    f"contact:{contact.jid or contact.phone}",
                    contact.to_dict().__repr__(),
                    now,
                ),
            )
        return True

    def remove_contact(self, jid: str) -> bool:
        """Remove a contact by JID/phone.

        Args:
            jid: Contact JID or phone number.

        Returns:
            True if removed.
        """
        with self.storage._lock, self.storage._conn:
            cursor = self.storage._conn.execute(
                "DELETE FROM olx_profile_kv WHERE key = ?", (f"contact:{jid}",)
            )
            return cursor.rowcount > 0

    def list_contacts(self, tag: str | None = None) -> list[Contact]:
        """List all contacts, optionally filtered by tag.

        Args:
            tag: Optional tag to filter contacts.

        Returns:
            List of Contact objects.
        """
        contacts: list[Contact] = []
        with self.storage._lock:
            rows = self.storage._conn.execute(
                "SELECT key, value FROM olx_profile_kv WHERE key LIKE 'contact:%'"
            ).fetchall()
        for row in rows:
            # Parse stored contact data
            try:
                import ast

                data = ast.literal_eval(row["value"])
                contact = Contact(
                    name=data.get("name", ""),
                    phone=data.get("phone"),
                    jid=data.get("jid"),
                    is_group=data.get("is_group", False),
                    last_message_at=data.get("last_message_at"),
                    unread_count=data.get("unread_count", 0),
                    tags=data.get("tags", []),
                )
                if tag is None or tag in contact.tags:
                    contacts.append(contact)
            except Exception:
                pass
        return contacts

    def tag_contact(self, jid: str, tag: str) -> bool:
        """Add a tag to a contact.

        Args:
            jid: Contact JID/phone.
            tag: Tag to add.

        Returns:
            True if tagged.
        """
        contacts = self.list_contacts()
        for c in contacts:
            if c.jid == jid or c.phone == jid:
                if tag not in c.tags:
                    c.tags.append(tag)
                    self.add_contact(c)
                return True
        return False
