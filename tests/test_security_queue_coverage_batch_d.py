"""Coverage for advanced security, zero trust and distributed queue."""

from aios_core.advanced_security import AdvancedSecurity, SecurityPolicy, ThreatLevel
from aios_core.distributed_queue import DistributedQueue, TaskPriority, TaskStatus
from aios_core.zero_trust import DeviceProfile, TrustEngine, TrustLevel, TrustPolicy, ZeroTrust


def test_advanced_security_detects_sanitizes_keys_and_resolves_threats():
    security = AdvancedSecurity()
    security.add_policy(SecurityPolicy("custom", "custom", ThreatLevel.LOW, lambda req: req.get("flag")))
    assert security.detect_threat({"ip": "127.0.0.1", "body": "<script>x</script>; DROP table", "flag": True})
    assert security.sanitize('<b onclick="x">javascript:hello</b>') == 'hello'
    signature = security.hmac_sign("body", "key")
    assert security.verify_hmac("body", "key", signature)
    key = security.generate_api_key("service")
    assert security.validate_api_key(key)
    replacement = security.rotate_api_key(key)
    assert not security.validate_api_key(key) and security.validate_api_key(replacement)
    assert security.resolve_threat("xss_attempt") == 1
    assert security.get_threats(unresolved_only=True)
    assert security.stats()["api_keys"] == 2


def test_zero_trust_profiles_policies_networks_and_facade():
    profile = DeviceProfile("d1", platform="olx", ip_address="8.8.8.8", fingerprint="fp", attributes={"verified_device": True, "mfa_enabled": True})
    engine = TrustEngine()
    engine.register_device(profile)
    assert profile.trust_level() == TrustLevel.FULLY_TRUSTED
    engine.add_policy(TrustPolicy("write", "write", TrustLevel.HIGH, {"role": ["admin"]}))
    assert engine.verify({"authenticated": True, "device_id": "d1", "resource": "write", "role": "admin"})
    assert not engine.verify({"authenticated": False})
    assert engine.check_network_segment("192.168.1.2", ["192.168.1.0/24"])
    assert not engine.check_network_segment("bad", ["192.168.1.0/24"])
    engine.revoke_device("d1")
    assert engine.verify_device("missing") == 0.0
    facade = ZeroTrust()
    facade.add_policy("read", {"resource": "read", "min_trust": 25})
    assert facade.verify({"authenticated": True, "authorized": True})
    assert facade.stats()["policies"] == 1


def test_distributed_queue_priorities_workers_retries_and_dead_letter():
    queue = DistributedQueue()
    worker = queue.register_worker("w", capacity=1)
    low = queue.enqueue({}, "low", TaskPriority.LOW)
    high = queue.enqueue({}, "high", TaskPriority.HIGH, max_retries=1)
    task = queue.dequeue()
    assert task.id == high.id and task.worker_id == "w"
    queue.fail(task.id, "retry")
    assert task.status == TaskStatus.RETRYING and worker.failed_tasks == 1
    retried = queue.dequeue()
    queue.fail(retried.id, "dead")
    assert queue.dead_letter_count() == 1
    assert queue.retry_dead_letter(retried.id)
    replay = queue.dequeue()
    queue.complete(replay.id, {"ok": True})
    assert queue.completed_count() == 1 and worker.completed_tasks == 1
    assert queue.dequeue().id == low.id
    assert queue.purge_dead_letter() == 0
    queue.unregister_worker("w")
    assert queue.stats()["total_tasks"] == 2
