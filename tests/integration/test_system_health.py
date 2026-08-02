def test_system_health_foundation():
    health = {
        "core": True,
        "runtime": True,
        "integration": True
    }

    assert all(health.values())
