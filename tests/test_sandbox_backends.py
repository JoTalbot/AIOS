from aios_core.runtime.sandbox_backends import SandboxRequest, SandboxResult


def test_sandbox_request_is_immutable_and_backend_result_is_structured():
    request = SandboxRequest(command=("python", "-c", "pass"))
    result = SandboxResult(returncode=0, stdout="ok", stderr="")
    assert request.command[0] == "python"
    assert result.returncode == 0
    assert result.stdout == "ok"
