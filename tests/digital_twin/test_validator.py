from aios.digital_twin.validator import validate_components


def test_lifecycle_validation():
    assert validate_components([
        "simulation",
        "prediction",
        "sync",
        "health",
        "audit",
    ])


def test_incomplete_validation():
    assert not validate_components(["simulation"])
