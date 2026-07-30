from swarm.ops.restart_policy import derive_restart_policy, validate_restart_policy, validate_registry


def test_parent_defaults_to_no_restart():
    p = derive_restart_policy({"id": "parent", "ip": "127.0.0.1", "role": "parent", "external": False})
    assert p.check_type == "tcp_only"
    assert p.strategy == "none"


def test_local_child_defaults_to_quarantine_only_not_ssh():
    p = derive_restart_policy({"id": "child", "ip": "127.0.0.1", "role": "child", "external": False})
    assert p.strategy == "quarantine_only"
    assert validate_restart_policy({"id": "child", "ip": "127.0.0.1", "external": False}) == []


def test_local_ssh_remote_is_rejected():
    errors = validate_restart_policy({"id": "bad", "ip": "127.0.0.1", "restart": {"strategy": "ssh_remote", "target": "octopus.service"}})
    assert any("ssh_remote" in e for e in errors)
    assert any("octopus.service" in e for e in errors)


def test_target_required_for_restart_strategy():
    errors = validate_restart_policy({"id": "remote", "ip": "203.0.113.10", "external": True, "restart": {"strategy": "ssh_remote"}})
    assert any("target is required" in e for e in errors)


def test_registry_validation_accepts_current_safe_defaults():
    registry = {"nodes": [{"id": "parent", "ip": "127.0.0.1", "role": "parent", "external": False}]}
    assert validate_registry(registry) == []
