"""Fail-closed CI policy resolver using task type plus actual changed paths."""
from __future__ import annotations

from dataclasses import dataclass

from .ci_policy import CIPolicy, policy_for
from .task_profiles import TaskType

SECURITY_WORKFLOWS = ("Supply Chain Gate", "Secret scanning")
SECURITY_PATH_MARKERS = (
    ".github/workflows/", "security", "auth", "permission", "permissions",
    "crypto", "cryptography", "secret", "secrets", "token", "oauth", "jwt",
    "middleware", "dependency", "requirements", "pyproject.toml", "poetry.lock",
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
)

@dataclass(frozen=True)
class ResolvedCIPolicy:
    base: CIPolicy
    task_type: TaskType
    security_forced: bool
    required_workflows: tuple[str, ...]
    reasons: tuple[str, ...]

def _is_security_sensitive(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return any(marker in normalized for marker in SECURITY_PATH_MARKERS)

def resolve_ci_policy(description: str, changed_files: list[str] | tuple[str, ...]) -> ResolvedCIPolicy:
    base = policy_for(description)
    reasons: list[str] = []
    forced = base.task_type == TaskType.SECURITY
    if forced:
        reasons.append("task_type:security")
    for path in changed_files:
        if _is_security_sensitive(path):
            forced = True
            reasons.append(f"sensitive_path:{path}")
    workflows = list(base.required_workflows)
    if forced:
        for workflow in SECURITY_WORKFLOWS:
            if workflow not in workflows:
                workflows.append(workflow)
    return ResolvedCIPolicy(base, base.task_type, forced, tuple(workflows), tuple(dict.fromkeys(reasons)))
