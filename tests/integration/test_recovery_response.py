from core.runtime.production_error_recovery import ProductionErrorRecovery
from core.runtime.response_error import ErrorResponse


def test_recovery_and_error_response():
    result = ProductionErrorRecovery().recover(Exception("failure"))
    assert result.recovered is False
    assert ErrorResponse("ERR", "failure").code == "ERR"
