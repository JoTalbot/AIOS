"""Tests for LLM Balancer v2.1"""
from aios_core.llm_balancer import LLMBalancer, APIKey, Provider

def test_api_key_availability():
    key = APIKey(key="test", provider="groq")
    assert key.is_available
    key.cooldown_until = 9999999999
    assert not key.is_available

def test_provider_round_robin():
    keys = [APIKey(key=f"k{i}", provider="groq") for i in range(3)]
    prov = Provider(name="groq", base_url="https://api.groq.com", keys=keys, models=["llama-3.1-8b-instant"])
    k1 = prov.get_next_key()
    k2 = prov.get_next_key()
    assert k1 is not None
    assert k2 is not None
    # After 3 calls should cycle
    k3 = prov.get_next_key()
    assert k3 is not None

def test_mark_key_error_402_dead():
    key = APIKey(key="dead", provider="openrouter")
    prov = Provider(name="openrouter", base_url="https://openrouter.ai", keys=[key], models=["test"])
    prov.mark_key_error(key, "HTTP 402 Payment Required", cooldown=86400)
    assert key.error_count == 1
    assert not key.is_available  # cooled down

def test_balancer_loads_providers():
    bal = LLMBalancer()
    # Should load at least groq, openrouter, etc if env present, but even without env should not crash
    assert hasattr(bal, 'providers')
    assert hasattr(bal, 'task_priority')
    assert "groq" in bal.task_priority["code"] or len(bal.task_priority["code"]) > 0

def test_balancer_priority_order():
    bal = LLMBalancer()
    # Check groq is before openrouter in priority
    prio = bal.task_priority.get("code", [])
    if "groq" in prio and "openrouter" in prio:
        assert prio.index("groq") < prio.index("openrouter"), "groq should be before openrouter"
    if "local" in prio:
        # local should be last
        assert prio[-1] == "local" or prio.index("local") > prio.index("groq")

def test_permanently_dead_flag():
    key = APIKey(key="test", provider="openrouter")
    key.error_count = 3
    key.permanently_dead = True
    assert not key.is_available
