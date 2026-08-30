from dataclasses import dataclass

@dataclass
class FederationHealth:
    active_nodes: int
    healthy: bool
    issues: list

class FederationHealthChecker:
    def check(self, federation):
        issues = []
        if not federation.nodes:
            issues.append("no active nodes")
        return FederationHealth(
            active_nodes=len(federation.nodes),
            healthy=len(issues) == 0,
            issues=issues,
        )
