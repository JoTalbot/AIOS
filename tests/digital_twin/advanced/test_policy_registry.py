from aios.digital_twin.capability_registry import CapabilityRegistry
from aios.digital_twin.policy import TwinPolicy


def test_capability_registry():
    registry = CapabilityRegistry()
    registry.register("forecast", {"version": "1"})
    assert registry.supports("forecast")
    assert registry.list() == ["forecast"]


def test_policy_requires_approval():
    policy = TwinPolicy(allowed_actions={"scale"})
    assert not policy.authorize("scale")
    assert policy.authorize("scale", approved=True)
    assert not policy.authorize("delete", approved=True)
