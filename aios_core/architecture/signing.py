"""Canonical HMAC signing without storing or logging secret material."""

import hashlib
import hmac
import json
from typing import Any


class HMACSigner:
    def __init__(self, key: bytes, key_id: str) -> None:
        if len(key) < 32:
            raise ValueError("signing key must be at least 32 bytes")
        self._key = key
        self.key_id = key_id

    @staticmethod
    def canonical(payload: dict[str, Any]) -> bytes:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

    def sign(self, payload: dict[str, Any]) -> str:
        return hmac.new(self._key, self.canonical(payload), hashlib.sha256).hexdigest()

    def verify(self, payload: dict[str, Any], signature: str) -> bool:
        return hmac.compare_digest(self.sign(payload), signature)
