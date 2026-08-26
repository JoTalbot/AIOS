from core.kernel.bootstrap import KernelBootstrap


def test_kernel_bootstrap_flow():
    bootstrap = KernelBootstrap()

    bootstrap.initialize()

    assert bootstrap is not None

    bootstrap.shutdown()
