#!/usr/bin/env python3
"""Resolve private call folders against a runtime Google Contacts cache.

The contact cache contains personal data and is deliberately stored outside Git.
Set ``AIOS_GOOGLE_CONTACTS_CACHE`` to override its private runtime location.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

CONTACTS_CACHE_FILE = Path(
    os.environ.get(
        "AIOS_GOOGLE_CONTACTS_CACHE",
        "/srv/aios-private/Calls/.google_contacts_cache.json",
    )
)
CALLS_DIR = Path(os.environ.get("AIOS_CALLS_DIR", "/root/AIOS/Calls"))
logger = logging.getLogger("aios.google_contacts")


def load_google_contacts() -> list[dict[str, Any]]:
    """Load contacts from the private runtime cache; never synthesize PII."""
    try:
        value = json.loads(CONTACTS_CACHE_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("Google Contacts cache is not configured")
        return []
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        logger.warning("Cannot read Google Contacts cache: %s", exc)
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        logger.warning("Google Contacts cache must contain a JSON list of objects")
        return []
    return value


def match_folder_to_google_contact(folder_name: str, file_path: str = "") -> dict[str, Any]:
    """Match a private call-folder label to a runtime contact record."""
    del file_path  # Kept for compatibility with existing callers.
    clean_name = folder_name.strip()

    # Date-like exported folders may need the actual parent folder from Calls.
    if re.match(r"^\d{2}-[а-яА-ЯA-Za-z]+", clean_name) or "Контакт 26-" in clean_name:
        stem = clean_name.replace("Контакт ", "").replace("_summary", "").strip()
        for audio in CALLS_DIR.rglob(f"{stem}.*"):
            if audio.parent != CALLS_DIR and audio.parent.name != "Calls":
                real_folder = audio.parent.name
                if "ambient" in real_folder.lower() or "!voice" in real_folder.lower():
                    clean_name = "Запись окружения (Диктофон)"
                else:
                    clean_name = real_folder
                break

    contacts = load_google_contacts()
    for contact in contacts:
        name = str(contact.get("name", ""))
        if name and name.casefold() == clean_name.casefold():
            return contact

    digits = re.sub(r"\D", "", clean_name)
    if digits:
        for contact in contacts:
            contact_digits = re.sub(r"\D", "", str(contact.get("phone", "")))
            if contact_digits and (digits in contact_digits or contact_digits in digits):
                return contact

    initials = "".join(word[0].upper() for word in clean_name.split()[:2]) if clean_name else "К"
    return {
        "id": f"g_{digits or hash(clean_name)}",
        "name": clean_name if not digits else f"Контакт {clean_name}",
        "phone": clean_name if digits else "",
        "initials": initials,
        "role": "Google Контакт",
    }


if __name__ == "__main__":
    print(f"Загружено контактов Google: {len(load_google_contacts())}")
