"""Verify reported file changes against authoritative git reality and RBAC paths."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable

from .handoff import AgentHandoff
from .models import AgentRole
from .permissions import check_paths


@dataclass(frozen=True)
class FileEvidence:
    passed: bool
    actual: tuple[str, ...]
    reported: tuple[str, ...]
    missing_from_handoff: tuple[str, ...] = ()
    uncommitted_or_unreported: tuple[str, ...] = ()
    permission_errors: tuple[str, ...] = ()


def _normalize(paths: Iterable[str]) -> tuple[str, ...]:
    values = set()
    for raw in paths:
        path = str(raw).strip().replace("\\", "/")
        if not path or path.startswith("/") or "\x00" in path:
            continue
        normalized = str(PurePosixPath(path))
        if normalized == "." or normalized.startswith("../") or "/../" in normalized:
            continue
        values.add(normalized)
    return tuple(sorted(values))


def verify_handoff_files(
    role: AgentRole,
    handoff: AgentHandoff,
    actual_files: Iterable[str],
) -> FileEvidence:
    """Require exact path agreement and enforce the canonical role permission matrix."""
    actual = _normalize(actual_files)
    reported = _normalize(handoff.files_changed)
    missing = tuple(sorted(set(actual) - set(reported)))
    extra = tuple(sorted(set(reported) - set(actual)))
    _, denied = check_paths(role, list(actual))
    passed = not missing and not extra and not denied
    return FileEvidence(passed, actual, reported, missing, extra, tuple(sorted(denied)))
