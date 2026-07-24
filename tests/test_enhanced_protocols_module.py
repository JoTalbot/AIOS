"""Tests for aios_core/enhanced_protocols.py"""
from __future__ import annotations
import pytest
from aios_core.enhanced_protocols import (
    ProtocolManager, GrpcAdapter, AmqpAdapter, WebSocketAdapter, MqttAdapter,
    ProtocolConfig, ProtocolType,
)


class TestProtocolManager:
    def test_create(self):
        pm = ProtocolManager()
        assert pm is not None

    def test_add_adapter(self):
        pm = ProtocolManager()
        config = ProtocolConfig(protocol_type=ProtocolType.GRPC, host="localhost", port=50051)
        adapter = GrpcAdapter(config=config)
        pm.add_adapter(ProtocolType.GRPC, adapter)

    @pytest.mark.asyncio
    async def test_start_all(self):
        pm = ProtocolManager()
        assert await pm.start_all()

    @pytest.mark.asyncio
    async def test_stop_all(self):
        pm = ProtocolManager()
        assert await pm.stop_all()


class TestGrpcAdapter:
    def test_create(self):
        config = ProtocolConfig(protocol_type=ProtocolType.GRPC, host="localhost", port=50051)
        a = GrpcAdapter(config=config)
        assert a is not None

    def test_add_service(self):
        config = ProtocolConfig(protocol_type=ProtocolType.GRPC, host="localhost", port=50051)
        a = GrpcAdapter(config=config)
        a.add_service("TestService", {})


class TestAmqpAdapter:
    def test_create(self):
        config = ProtocolConfig(protocol_type=ProtocolType.AMQP, host="localhost", port=5672)
        a = AmqpAdapter(config=config)
        assert a is not None


class TestWebSocketAdapter:
    def test_create(self):
        config = ProtocolConfig(protocol_type=ProtocolType.WEBSOCKET, host="0.0.0.0", port=8765)
        a = WebSocketAdapter(config=config)
        assert a is not None


class TestMqttAdapter:
    def test_create(self):
        config = ProtocolConfig(protocol_type=ProtocolType.MQTT, host="localhost", port=1883)
        a = MqttAdapter(config=config)
        assert a is not None
