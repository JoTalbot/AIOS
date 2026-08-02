from aios_core.v5.communication.bus import AgentCommunicationBus


def test_agent_message_bus():
    bus = AgentCommunicationBus()
    message = bus.publish("olx_agent", "analyzer", {"task": "analyze"})

    assert message["sender"] == "olx_agent"
    assert len(bus.history()) == 1
