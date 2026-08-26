from dataclasses import dataclass


@dataclass
class SandboxContext:
    sandbox_id: str
    isolated: bool = True


class SandboxManager:
    """Isolation boundary for AIOS runtime execution."""

    def create(self, sandbox_id: str):
        return SandboxContext(sandbox_id=sandbox_id)

    def destroy(self, context: SandboxContext):
        return {"sandbox": context.sandbox_id, "status": "destroyed"}
