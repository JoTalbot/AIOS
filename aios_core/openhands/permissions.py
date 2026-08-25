"""Права ролей OpenHands-контура поверх существующих механизмов AIOS.

RBAC — ``aios_core.rbac.RBACEngine`` (роли регистрируются как ``oh-<role>``);
protected-пути — ``aios_core.self_protection.is_protected`` (единый канонический
список). Дублирующих механизмов не создаётся.
"""

import fnmatch

from aios_core.rbac import RBACEngine
from aios_core.self_protection import is_protected

from .models import MVP_ROLES, AgentPermissions, AgentProfile, AgentRole

RBAC_ROLE_PREFIX = "oh-"


def _perms(**kw) -> AgentPermissions:
    return AgentPermissions(**kw)


# Матрица прав (Этап 14 master-плана): минимально необходимый доступ на роль.
PROFILES: dict[AgentRole, AgentProfile] = {
    AgentRole.ORCHESTRATOR: AgentProfile(
        role=AgentRole.ORCHESTRATOR,
        permissions=_perms(
            read="all",
            write="orchestration",
            allowed_paths=("data/openhands/**", "coordination/**"),
            deny_paths=("**/*.py",),
            secret_allowlist=(),
        ),
        memory_scope="orchestration",
    ),
    AgentRole.ARCHITECT: AgentProfile(
        role=AgentRole.ARCHITECT,
        permissions=_perms(
            read="all",
            write="reports",
            allowed_paths=("docs/design/**",),
            secret_allowlist=(),
        ),
    ),
    AgentRole.CODER: AgentProfile(
        role=AgentRole.CODER,
        permissions=_perms(
            read="project",
            write="workspace",
            allowed_paths=("**",),
            deny_paths=(".env*", "data/.llm_keys.json", "**/*secret*", "**/*token*"),
            secret_allowlist=(),
        ),
    ),
    AgentRole.TESTER: AgentProfile(
        role=AgentRole.TESTER,
        permissions=_perms(
            read="project",
            write="reports",
            allowed_paths=("tests/**", "reports/**"),
            secret_allowlist=(),
        ),
    ),
    AgentRole.REVIEWER: AgentProfile(
        role=AgentRole.REVIEWER,
        permissions=_perms(
            read="all",
            write="reports",
            allowed_paths=("reports/reviews/**",),
            secret_allowlist=(),
        ),
    ),
    # Пост-MVP: подключаются после зелёного MVP (план, §5).
    AgentRole.SECURITY: AgentProfile(
        role=AgentRole.SECURITY,
        permissions=_perms(read="all", write="reports", allowed_paths=("reports/security/**",)),
    ),
    AgentRole.QA: AgentProfile(
        role=AgentRole.QA,
        permissions=_perms(read="all", write="reports", allowed_paths=("reports/qa/**",)),
    ),
}

# RBAC-пермишены на роль (resource:action, wildcards по aios_core/rbac.py).
_RBAC_PERMISSIONS: dict[AgentRole, tuple[str, ...]] = {
    AgentRole.ORCHESTRATOR: ("repo:read", "orchestration:write", "audit:write"),
    AgentRole.ARCHITECT: ("repo:read", "docs:write"),
    AgentRole.CODER: ("repo:read", "workspace:write"),
    AgentRole.TESTER: ("repo:read", "tests:write", "reports:write"),
    AgentRole.REVIEWER: ("repo:read", "reports:write"),
    AgentRole.SECURITY: ("repo:read", "reports:write"),
    AgentRole.QA: ("repo:read", "reports:write"),
}


def rbac_role_name(role: AgentRole) -> str:
    """Имя роли контура в RBACEngine."""
    return f"{RBAC_ROLE_PREFIX}{role.value}"


def register_roles(engine: RBACEngine, roles: tuple[AgentRole, ...] = MVP_ROLES) -> list[str]:
    """Зарегистрировать роли контура в существующем RBACEngine (идемпотентно).

    Возвращает имена зарегистрированных (или уже существовавших) ролей.
    """
    registered: list[str] = []
    for role in roles:
        name = rbac_role_name(role)
        if name not in engine.hierarchy.roles:
            engine.create_role(
                name,
                permissions=list(_RBAC_PERMISSIONS.get(role, ("repo:read",))),
                description=f"OpenHands contour role: {role.value}",
            )
        registered.append(name)
    return registered


def path_allowed(path: str, permissions: AgentPermissions) -> bool:
    """Разрешена ли роли запись в ``path`` (относительный путь от корня репо).

    Порядок: deny_paths → allowed_paths (glob, ``**`` = любые уровни).
    """
    rel = path.replace("\\", "/").lstrip("/")
    if any(fnmatch.fnmatch(rel, pat) for pat in permissions.deny_paths):
        return False
    return any(fnmatch.fnmatch(rel, pat) for pat in permissions.allowed_paths)


def check_paths(role: AgentRole, paths: list[str]) -> tuple[list[str], list[str]]:
    """Разбить изменённые файлы на (allowed, denied) для роли.

    Denied также включает protected-файлы (``self_protection.is_protected``) —
    они вне полномочий любой роли контура независимо от allowed_paths.
    """
    profile = PROFILES[role]
    allowed: list[str] = []
    denied: list[str] = []
    for path in paths:
        if is_protected(path) or not path_allowed(path, profile.permissions):
            denied.append(path)
        else:
            allowed.append(path)
    return allowed, denied
