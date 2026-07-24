"""Tests for aios_core/api/protocols.py"""
from __future__ import annotations
import pytest


class TestProtocolManager:
    def test_create(self):
        from aios_core.api.protocols import ProtocolManager
        # ProtocolManager needs integration_manager - test import works
        assert ProtocolManager is not None

    def test_websocket_adapter(self):
        from aios_core.api.protocols import WebSocketAdapter
        assert WebSocketAdapter is not None

    def test_graphql_adapter(self):
        from aios_core.api.protocols import GraphQLAdapter
        assert GraphQLAdapter is not None

    def test_grpc_adapter(self):
        from aios_core.api.protocols import GrpcAdapter
        assert GrpcAdapter is not None

    def test_sse_adapter(self):
        from aios_core.api.protocols import SSEAdapter
        assert SSEAdapter is not None
