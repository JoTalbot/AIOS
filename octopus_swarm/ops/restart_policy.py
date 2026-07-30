from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

LOCAL_IPS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}
SAFE_STRATEGIES = {"none", "quarantine_only", "local_container", "local_systemd", "ssh_remote"}


@dataclass(frozen=True)
class RestartPolicy:
    node_id: str
    check_type: str
    strategy: str
    target: str | None
    parent_restart_allowed: bool = False
    max_restarts: int = 1
    window_seconds: int = 900


def _restart_block(node: Mapping[str, Any]) -> Mapping[str, Any]:
    block = node.get("restart")
    if isinstance(block, Mapping):
        return block
    strategy = node.get("restart_strategy")
    if strategy:
        return {"strategy": strategy, "target": node.get("restart_target")}
    return {}


def is_local_or_tunnel(node: Mapping[str, Any]) -> bool:
    ip = str(node.get("ip") or "")
    tags = {str(t).lower() for t in node.get("tags", []) or []}
    return ip in LOCAL_IPS or "local" in tags or "tunneled" in tags or node.get("external") is False


def derive_restart_policy(node: Mapping[str, Any]) -> RestartPolicy:
    node_id = str(node.get("id") or "unknown")
    role = str(node.get("role") or "").lower()
    block = _restart_block(node)
    check_type = str(node.get("check_type") or ("tcp_only" if is_local_or_tunnel(node) else "http"))

    if role == "parent":
        default_strategy = "none"
    elif is_local_or_tunnel(node):
        default_strategy = "quarantine_only"
    else:
        default_strategy = "quarantine_only"

    strategy = str(block.get("strategy") or default_strategy)
    budget = block.get("budget") if isinstance(block.get("budget"), Mapping) else {}
    return RestartPolicy(
        node_id=node_id,
        check_type=check_type,
        strategy=strategy,
        target=block.get("target") or node.get("restart_target"),
        parent_restart_allowed=bool(block.get("parent_restart_allowed", False)),
        max_restarts=int(budget.get("max_restarts", 1)),
        window_seconds=int(budget.get("window_seconds", 900)),
    )


def validate_restart_policy(node: Mapping[str, Any]) -> list[str]:
    policy = derive_restart_policy(node)
    errors: list[str] = []
    if policy.strategy not in SAFE_STRATEGIES:
        errors.append(f"{policy.node_id}: invalid restart strategy {policy.strategy!r}")
    if is_local_or_tunnel(node) and policy.strategy == "ssh_remote":
        errors.append(f"{policy.node_id}: local/tunnel node must not use ssh_remote")
    if policy.target == "octopus.service" and not policy.parent_restart_allowed:
        errors.append(f"{policy.node_id}: octopus.service restart requires explicit parent_restart_allowed")
    if policy.strategy in {"local_container", "local_systemd", "ssh_remote"} and not policy.target:
        errors.append(f"{policy.node_id}: restart target is required for {policy.strategy}")
    if policy.max_restarts < 0 or policy.window_seconds <= 0:
        errors.append(f"{policy.node_id}: invalid restart budget")
    return errors


def validate_registry(registry: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for node in registry.get("nodes", []) or []:
        if isinstance(node, Mapping):
            errors.extend(validate_restart_policy(node))
    return errors
