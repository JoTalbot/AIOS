class FederationValidator:
    def validate(self, federation):
        return {
            "valid": bool(federation.federation_id),
            "nodes": len(federation.nodes),
            "topology_consistent": isinstance(federation.topology, dict),
        }
