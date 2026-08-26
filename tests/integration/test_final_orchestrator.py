def test_readiness_imports():
    from core.runtime.readiness_check import ReadinessCheck
    assert ReadinessCheck().run()["status"] == "ready"
