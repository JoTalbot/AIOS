"""AIOS Bootstrap Layer v2.1.1

Entry point that wires the core layers together and runs an action through the
full lifecycle, now driven by the Orchestrator.
"""

from .policy_loader import PolicyLoader
from .orchestrator import Orchestrator


class AIOSBootstrap:
    """Bootstraps the AIOS core and processes actions end-to-end."""

    def __init__(self, policy_loader=None):
        self.policies = policy_loader if policy_loader is not None else PolicyLoader()
        self.orchestrator = Orchestrator(self.policies)

    def boot(self) -> dict:
        return {
            "status": "ready",
            "version": self.orchestrator.constitution.version,
            "policies_loaded": len(self.policies.policies),
        }

    def process(self, action: dict) -> dict:
        """Run an action through the full cognitive lifecycle."""
        return self.orchestrator.run(action)

    def report(self) -> dict:
        """Return orchestrator summary."""
        return self.orchestrator.report()


def _demo():
    boot = AIOSBootstrap()
    print("AIOS boot:", boot.boot())
    samples = [
        {"goal": "optimize_task", "scope": "local_module", "risk": "low",
         "reversible": True, "audit_log": True},
        {"goal": "rewrite_core", "scope": "global", "risk": "high",
         "reversible": False, "audit_log": True},
        {"goal": "unknown", "scope": "hidden"},
    ]
    for action in samples:
        print("---")
        print("action:", action)
        print("trace :", boot.process(action))
    print("---")
    print("report:", boot.report())


if __name__ == "__main__":
    _demo()
