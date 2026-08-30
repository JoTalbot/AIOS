from aios.federation.models import Federation, FederationNode
from aios.federation.federation import FederationRuntime


def test_register_and_discover_node():
    federation = Federation("test")
    runtime = FederationRuntime(federation)
    runtime.register_node(FederationNode("node-a"))
    assert len(runtime.discover_nodes()) == 1
