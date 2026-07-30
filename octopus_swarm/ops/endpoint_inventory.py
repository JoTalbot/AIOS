from __future__ import annotations

from dataclasses import dataclass

PUBLIC_EXPECTED_PORTS = {22, 80, 443}
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


@dataclass(frozen=True)
class Endpoint:
    proto: str
    host: str
    port: int
    process: str = ""


def classify_endpoint(ep: Endpoint) -> str:
    if ep.host in LOCAL_HOSTS or ep.host.startswith("127."):
        return "LOCAL_ONLY"
    if ep.port in PUBLIC_EXPECTED_PORTS:
        return "PUBLIC_EXPECTED"
    if ep.host in {"0.0.0.0", "::", "*"} or not ep.host.startswith("127."):
        return "PUBLIC_REVIEW"
    return "UNKNOWN"


def endpoint_risk_note(ep: Endpoint) -> str:
    klass = classify_endpoint(ep)
    if klass == "LOCAL_ONLY":
        return "loopback/internal"
    if klass == "PUBLIC_EXPECTED":
        return "expected public admin/web port; verify hardening"
    if klass == "PUBLIC_REVIEW":
        return "requires owner/auth/firewall/tunnel classification"
    return "manual review required"
