import json
from pathlib import Path

from swarm.ops.restart_policy import derive_restart_policy, validate_registry


def _registry():
    return json.loads(Path("config/nodes.json").read_text())


def test_current_node_registry_restart_policies_are_safe():
    assert validate_registry(_registry()) == []


def test_parent_nodes_default_to_no_parent_restart():
    parents = [n for n in _registry().get("nodes", []) if n.get("role") == "parent"]
    assert parents
    for node in parents:
        policy = derive_restart_policy(node)
        assert policy.strategy == "none"
        assert policy.parent_restart_allowed is False


def test_local_and_tunnel_nodes_do_not_use_ssh_remote():
    for node in _registry().get("nodes", []):
        tags = {str(t).lower() for t in node.get("tags", []) or []}
        localish = node.get("ip") in {"127.0.0.1", "localhost", "::1"} or "local" in tags or "tunneled" in tags
        if localish:
            assert derive_restart_policy(node).strategy != "ssh_remote"
