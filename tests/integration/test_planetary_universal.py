def test_planetary_universal_connection():
    from planetary.core.planetary_kernel import PlanetaryKernel
    from universal.core.universal_kernel import UniversalKernel

    planetary = PlanetaryKernel()
    universal = UniversalKernel()

    planetary.register(universal)

    assert universal in planetary.status()
