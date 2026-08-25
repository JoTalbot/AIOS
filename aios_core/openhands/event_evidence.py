"""Convert OpenHands event payloads into conservative completion evidence."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .evidence import CompletionReport, Evidence, EvidenceKind, dod_for_role


def _strings(node: Any):
    if isinstance(node, str):
        yield node
    elif isinstance(node, Mapping):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _strings(value)


def _event_kind(event: Mapping[str, Any]) -> str:
    for key in ("type", "event_type", "kind"):
        value = event.get(key)
        if isinstance(value, str):
            return value.lower()
    return ""


def build_completion_report(payload: Mapping[str, Any], role: str) -> CompletionReport:
    """Build evidence only from explicit runtime events; never infer success."""
    report = CompletionReport()
    events = payload.get("events", [])
    if not isinstance(events, list):
        return report

    for event in events:
        if not isinstance(event, Mapping):
            continue
        kind = _event_kind(event)
        text = " | ".join(_strings(event))
        if not text.strip():
            continue
        if kind in {"test", "test_result", "verification"}:
            report.evidence.append(Evidence(EvidenceKind.TEST, kind, text, "fail" not in text.lower() and "error" not in text.lower()))
        elif kind in {"command", "command_run", "shell"}:
            report.evidence.append(Evidence(EvidenceKind.COMMAND, kind, text, "exit code 0" in text.lower() or "success" in text.lower()))
        elif kind in {"compile", "py_compile"}:
            report.evidence.append(Evidence(EvidenceKind.COMPILE, kind, text, "fail" not in text.lower() and "error" not in text.lower()))
        elif kind in {"diff", "diff_check"}:
            report.evidence.append(Evidence(EvidenceKind.DIFF, kind, text, "fail" not in text.lower() and "error" not in text.lower()))
        elif kind in {"lint"}:
            report.evidence.append(Evidence(EvidenceKind.LINT, kind, text, "fail" not in text.lower() and "error" not in text.lower()))
        elif kind in {"security", "security_check"}:
            report.evidence.append(Evidence(EvidenceKind.SECURITY, kind, text, "fail" not in text.lower() and "error" not in text.lower()))
        elif kind in {"review", "review_result"}:
            report.evidence.append(Evidence(EvidenceKind.REVIEW, kind, text, "CHANGES_REQUESTED" not in text))

        if "DOD:" in text:
            for item in text.split("DOD:", 1)[1].splitlines()[0].split(","):
                key, sep, value = item.strip().partition("=")
                if sep and key in {dod.key for dod in dod_for_role(role)}:
                    report.dod[key] = value.strip().lower() in {"true", "pass", "passed", "yes"}

    return report
