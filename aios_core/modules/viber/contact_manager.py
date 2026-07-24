"""Viber contact manager — inherits WhatsApp ContactManager for Viber platform."""

from aios_core.modules.whatsapp.contact_manager import ContactManager, Contact


class ViberContactManager(ContactManager):
    """Contact manager for Viber — same interface as WhatsApp."""
