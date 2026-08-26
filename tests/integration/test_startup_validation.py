from core.runtime.startup_validation import StartupValidator


def test_startup_validation():
    result = StartupValidator().validate()
    assert result.ready
