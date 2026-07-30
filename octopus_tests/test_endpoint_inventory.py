from swarm.ops.endpoint_inventory import Endpoint, classify_endpoint, endpoint_risk_note


def test_loopback_is_local_only():
    ep = Endpoint("tcp", "127.0.0.1", 5432, "postgres")
    assert classify_endpoint(ep) == "LOCAL_ONLY"
    assert "loopback" in endpoint_risk_note(ep)


def test_web_ports_are_expected_public():
    assert classify_endpoint(Endpoint("tcp", "0.0.0.0", 443, "nginx")) == "PUBLIC_EXPECTED"
    assert classify_endpoint(Endpoint("tcp", "0.0.0.0", 80, "nginx")) == "PUBLIC_EXPECTED"


def test_unknown_public_port_requires_review():
    ep = Endpoint("tcp", "0.0.0.0", 9555, "python3")
    assert classify_endpoint(ep) == "PUBLIC_REVIEW"
    assert "requires owner" in endpoint_risk_note(ep)
