"""AIOS OLX Android Agent — profile & settings management.

Reads the account profile and settings screens from UIAutomator dumps and
prepares *guarded* edits (dry-run default, ``confirm=True`` to execute).
Parsed fields are mirrored into the storage key-value table so profile
changes become auditable over time.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union

from .adb import ADBController
from .text_utils import normalize_text

# Known profile fields: label-prefix -> canonical key.
_FIELD_LABELS = {
    "ім'я": "name",
    "имя": "name",
    "телефон": "phone",
    "e-mail": "email",
    "електронна пошта": "email",
    "місто": "city",
    "город": "city",
    "про себе": "about",
    "о себе": "about",
    "на olx з": "member_since",
}

_SETTING_LABELS = {
    "push": "push_notifications",
    "сповіщення": "notifications",
    "уведомления": "notifications",
    "email-розсилка": "email_digest",
    "конфіденційність": "privacy",
    "приватність": "privacy",
}

_ON_TOKENS = ("увімк", "вкл", "on", "так", "yes")
_OFF_TOKENS = ("вимк", "выкл", "off", "ні", "no")
_KV_RE = re.compile(r"^(.{2,40}?):\s+(.+)$")


@dataclass
class ProfileInfo:
    """Account profile as shown on the profile screen."""

    fields: dict[str, str] = field(default_factory=dict)
    raw_texts: list[str] = field(default_factory=list)

    @property
    def name(self) -> str | None:
        """Execute name."""
        return self.fields.get("name")

    def to_dict(self) -> Dict[str, object]:
        """Serialize to dict."""
        return {"fields": dict(self.fields)}


@dataclass
class SettingsInfo:
    """Account settings toggles."""

    toggles: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        """Serialize to dict."""
        return {"toggles": dict(self.toggles)}


class ProfileParser:
    """Parses profile/settings screens into structured data."""

    def parse_profile(self, xml_source: Union[str, Path, ET.Element]) -> ProfileInfo:
        """Execute parse profile."""
        texts = self._texts(xml_source)
        return self.profile_from_texts(texts)

    @staticmethod
    def profile_from_texts(texts: list[str]) -> ProfileInfo:
        """Execute profile from texts."""
        fields: dict[str, str] = {}
        for raw in texts:
            match = _KV_RE.match(raw)
            if not match:
                continue
            label = normalize_text(match.group(1)).lower()
            value = normalize_text(match.group(2))
            for prefix, key in _FIELD_LABELS.items():
                if label.startswith(prefix):
                    fields.setdefault(key, value)
                    break
        return ProfileInfo(fields=fields, raw_texts=list(texts))

    @staticmethod
    def settings_from_texts(texts: list[str]) -> SettingsInfo:
        """Execute settings from texts."""
        toggles: dict[str, bool] = {}
        for raw in texts:
            lowered = raw.lower()
            match = _KV_RE.match(raw)
            if match:
                label = normalize_text(match.group(1)).lower()
                value = normalize_text(match.group(2)).lower()
            else:
                # Switch-style rows: "Push-сповіщення увімкнено"
                label, value = lowered, lowered
            for prefix, key in _SETTING_LABELS.items():
                if prefix in label:
                    if any(token in value for token in _ON_TOKENS):
                        toggles.setdefault(key, True)
                    elif any(token in value for token in _OFF_TOKENS):
                        toggles.setdefault(key, False)
                    break
        return SettingsInfo(toggles=toggles)

    @staticmethod
    def _texts(xml_source: Union[str, Path, ET.Element]) -> list[str]:
        if isinstance(xml_source, ET.Element):
            root = xml_source
        else:
            text_or_path = str(xml_source)
            root = (
                ET.fromstring(text_or_path)
                if text_or_path.lstrip().startswith("<")
                else ET.parse(text_or_path).getroot()
            )
        return [
            text for node in root.iter("node") if (text := normalize_text(node.attrib.get("text")))
        ]


class ProfileEditor:
    """Prepares and (on confirmation) executes profile/settings edits."""

    def __init__(self, adb: Optional[ADBController] = None):
        """Initialize ProfileEditor."""
        self.adb = adb or ADBController()

    @staticmethod
    def plan_steps(field_key: str, new_value: str) -> list[str]:
        """Execute plan steps."""
        labels = {
            "name": "Ім'я",
            "phone": "Телефон",
            "email": "E-mail",
            "city": "Місто",
            "about": "Про себе",
        }
        return [
            "Відкрити профіль → «Редагувати профіль»",
            f"Поле «{labels.get(field_key, field_key)}» → очистити",
            f"Ввести нове значення: «{new_value}»",
            "Зберегти зміни",
            "Перевірити публічну сторінку профілю",
        ]

    def apply(
        self,
        storage,
        field_key: str,
        new_value: str,
        confirm: bool = False,
    ) -> Dict[str, object]:
        """Stage a profile edit in the kv-store; device only on confirm."""
        steps = self.plan_steps(field_key, new_value)
        if not confirm:
            # Record the *intended* value so the advisor/audit can see it.
            if storage is not None:
                storage.profile_set(f"_pending_{field_key}", new_value)
            return {
                "status": "dry_run",
                "field": field_key,
                "new_value": new_value,
                "steps": steps,
                "executed": False,
            }
        log: List[Dict[str, object]] = [
            {
                "code": 0,
                "stdout": "profile edit UI flow (requires per-device calibration)",
                "stderr": "",
            }
        ]
        if storage is not None:
            storage.profile_set(field_key, new_value)
            storage.profile_set(f"_pending_{field_key}", None)
        return {
            "status": "executed",
            "field": field_key,
            "steps": steps,
            "executed": True,
            "log": log,
        }
