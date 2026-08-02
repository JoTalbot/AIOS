def test_runtime_execution():
    from universal.core.universal_system import UniversalSystem

    system = UniversalSystem()
    result = system.initialize()

    assert result["initialized"] is True
