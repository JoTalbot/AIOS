"""A-Банк business API request builder, sandbox/dry-run only.

The public A-Банк business documentation describes HMAC-SHA256 signatures for
JSON requests.  This module builds and signs requests locally but never sends a
request by itself.  Live payments, loan applications, confirmations and
refunds are intentionally absent from the AIOS automation surface.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BusinessRequest:
    method: str
    endpoint: str
    body: str
    signature: str
    headers: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "endpoint": self.endpoint,
            "body": self.body,
            "signature": self.signature,
            "headers": dict(self.headers),
            "network_sent": False,
        }


def canonical_json(payload: Mapping[str, Any]) -> str:
    """Serialize request data deterministically for a reproducible signature."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


def sign_body(body: str, secret: str) -> str:
    if not secret:
        raise ValueError("secret is required for local signing")
    digest = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


class ABankBusinessAPI:
    """Build safe, non-sending A-Банк business API requests."""

    ALLOWED_ENDPOINTS = frozenset({
        "newLoan",
        "getLoanStatus",
        "getRefundStatus",
        "creditHistory",
        "getWarranty",
        "getWarrantyFile",
    })

    def build_request(self, endpoint: str, payload: Mapping[str, Any], *, secret: str) -> BusinessRequest:
        endpoint = str(endpoint).strip().strip("/")
        if endpoint not in self.ALLOWED_ENDPOINTS:
            raise ValueError("unsupported or write-sensitive business endpoint")
        body = canonical_json(payload)
        signature = sign_body(body, secret)
        return BusinessRequest(
            method="POST",
            endpoint=endpoint,
            body=body,
            signature=signature,
            headers={"Content-Type": "application/json", "signature": signature},
        )

    @staticmethod
    def safety_status() -> dict[str, Any]:
        return {
            "provider": "abank_business",
            "mode": "dry_run",
            "network_sent": False,
            "sandbox_request_builder": True,
            "live_requests": False,
            "payment_confirmation": False,
            "loan_confirmation": False,
            "refund_execution": False,
            "reason": "AIOS builds signatures only; a human/operator must integrate an approved sandbox separately.",
        }
