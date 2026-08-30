from .decisions import PolicyDecision


class Kernel:
    def __init__(self, identity, trust, policy, audit):
        self.identity = identity
        self.trust = trust
        self.policy = policy
        self.audit = audit

    def process(self, context):
        self.identity.validate(context.agent_id)
        trust = self.trust.evaluate(context.agent_id)
        decision = self.policy.evaluate(context, trust)
        self.audit.record(decision)
        return decision
