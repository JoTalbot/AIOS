"""kan smoke test."""
def test_kan(): from aios_core.kan import KANetwork; assert KANetwork().stats() is not None
