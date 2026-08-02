def test_universal_kernel_foundation():
    from universal.core.universal_kernel import UniversalKernel

    kernel = UniversalKernel()
    kernel.register("test_component")

    assert "test_component" in kernel.status()["components"]
    assert kernel.status()["ready"] is True
