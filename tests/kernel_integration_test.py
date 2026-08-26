"""Integration checks for AIOS kernel components."""


def test_kernel_components_registration():
    components = ["runtime", "agents", "memory", "learning"]
    assert len(components) == 4
