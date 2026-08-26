from dataclasses import dataclass


@dataclass
class GatewayResponse:
    accepted: bool
    decision: str
    audit_id: str | None = None


class ExecutionGateway:
    def __init__(self, policy_engine, audit_logger):
        self.policy_engine = policy_engine
        self.audit_logger = audit_logger

    def execute(self, request, capabilities):
        decision = self.policy_engine.evaluate(request, capabilities)

        event = self.audit_logger.record(
            actor=request.actor_id,
            action=request.action,
            result=decision.status.value
        )

        return GatewayResponse(
            decision.status.value == "allow",
            decision.status.value,
            event.id
        )
