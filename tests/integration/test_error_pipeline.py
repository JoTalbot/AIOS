from core.runtime.error_pipeline import ErrorPipeline


def test_error_pipeline():
    assert "error" in ErrorPipeline().handle(Exception("x"))
