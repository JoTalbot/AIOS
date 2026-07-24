"""AIOS MCP Protocol Engine v1.0.0

JSON-RPC 2.0 message codec for the Model Context Protocol.
Handles encoding/decoding of requests, responses, notifications, and errors.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class JSONRPCError(int, Enum):
    """Standard and AIOS-specific JSON-RPC error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    CONSTITUTION_DENIED = -32001
    CONSTITUTION_REVIEW = -32002
    TOOL_EXECUTION_ERROR = -32003
    RESOURCE_NOT_FOUND = -32004


class JSONRPCParseError(Exception):
    """Raised when a JSON-RPC message cannot be parsed."""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


@dataclass
class JSONRPCRequest:
    """A JSON-RPC 2.0 request with id, method, and params."""

    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str = ""
    params: dict = field(default_factory=dict)


@dataclass
class JSONRPCResponse:
    """A JSON-RPC 2.0 response with id and either result or error."""

    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: Any = None
    error: dict | None = None  # {"code": int, "message": str, "data": any}


@dataclass
class JSONRPCNotification:
    """A JSON-RPC 2.0 notification (no id, no response expected)."""

    jsonrpc: str = "2.0"
    method: str = ""
    params: dict = field(default_factory=dict)


class MCPProtocol:
    """JSON-RPC 2.0 codec for MCP messages.

    Provides static methods to parse raw JSON strings into typed objects
    and encode typed objects back into JSON strings.
    """

    @staticmethod
    def parse(raw: str) -> JSONRPCRequest | JSONRPCNotification | JSONRPCResponse:
        """Parse a JSON-RPC 2.0 message string into a typed object.

        Args:
            raw: JSON string to parse.

        Returns:
            One of JSONRPCRequest, JSONRPCNotification, or JSONRPCResponse.

        Raises:
            JSONRPCParseError: If the message is not valid JSON-RPC 2.0.
        """
        if not raw or not raw.strip():
            raise JSONRPCParseError(
                JSONRPCError.PARSE_ERROR,
                "Empty message",
            )

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise JSONRPCParseError(
                JSONRPCError.PARSE_ERROR,
                f"Invalid JSON: {exc}",
            ) from exc

        if not isinstance(data, dict):
            raise JSONRPCParseError(
                JSONRPCError.INVALID_REQUEST,
                "JSON-RPC message must be an object",
            )

        # Validate jsonrpc version
        jsonrpc_version = data.get("jsonrpc")
        if jsonrpc_version != "2.0":
            raise JSONRPCParseError(
                JSONRPCError.INVALID_REQUEST,
                f"Invalid or missing jsonrpc version: {jsonrpc_version!r}",
            )

        # Determine message type
        msg_id = data.get("id", None)
        has_result = "result" in data
        has_error = "error" in data
        has_method = "method" in data

        if has_method:
            if msg_id is None:
                # No id → notification
                return JSONRPCNotification(
                    jsonrpc="2.0",
                    method=data["method"],
                    params=data.get("params", {}),
                )
            else:
                # Has id and method → request
                return JSONRPCRequest(
                    jsonrpc="2.0",
                    id=msg_id,
                    method=data["method"],
                    params=data.get("params", {}),
                )

        if has_result or has_error:
            # Has result or error → response
            return JSONRPCResponse(
                jsonrpc="2.0",
                id=msg_id,
                result=data.get("result"),
                error=data.get("error"),
            )

        # Has id but neither method nor result/error
        raise JSONRPCParseError(
            JSONRPCError.INVALID_REQUEST,
            "Missing 'method', 'result', or 'error' field",
        )

    @staticmethod
    def encode_request(id: str | int, method: str, params: dict = None) -> str:
        """Encode a JSON-RPC 2.0 request.

        Args:
            id: Request identifier (string or integer).
            method: Method name to invoke.
            params: Optional parameters dict.

        Returns:
            JSON string.
        """
        msg = {
            "jsonrpc": "2.0",
            "id": id,
            "method": method,
        }
        if params:
            msg["params"] = params
        return json.dumps(msg, ensure_ascii=False)

    @staticmethod
    def encode_response(id: str | int, result: Any = None, error: dict = None) -> str:
        """Encode a JSON-RPC 2.0 response.

        Args:
            id: Request identifier being responded to.
            result: Successful result value.
            error: Error dict with code, message, and optional data.

        Returns:
            JSON string.
        """
        msg: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": id,
        }
        if error is not None:
            msg["error"] = error
        else:
            msg["result"] = result
        return json.dumps(msg, ensure_ascii=False)

    @staticmethod
    def encode_notification(method: str, params: dict = None) -> str:
        """Encode a JSON-RPC 2.0 notification (no id, no response).

        Args:
            method: Method name.
            params: Optional parameters dict.

        Returns:
            JSON string.
        """
        msg: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            msg["params"] = params
        return json.dumps(msg, ensure_ascii=False)

    @staticmethod
    def encode_error(id: str | int | None, code: int, message: str, data: Any = None) -> str:
        """Encode a JSON-RPC 2.0 error response.

        Args:
            id: Request identifier (None for errors on notifications/parse).
            code: Error code (int).
            message: Error message string.
            data: Optional additional error data.

        Returns:
            JSON string.
        """
        error_obj: dict[str, Any] = {
            "code": code,
            "message": message,
        }
        if data is not None:
            error_obj["data"] = data
        msg: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": id,
            "error": error_obj,
        }
        return json.dumps(msg, ensure_ascii=False)


# ---------------------------------------------------------------------------
# MCP-specific message types
# ---------------------------------------------------------------------------


@dataclass
class MCPToolCall:
    """Represents a tool invocation through MCP."""

    name: str
    arguments: dict
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


@dataclass
class MCPToolResult:
    """Result of a tool invocation."""

    content: list[dict]  # [{"type": "text", "text": "..."}]
    is_error: bool = False


@dataclass
class MCPResource:
    """An MCP resource descriptor."""

    uri: str
    name: str
    description: str = ""
    mime_type: str = "text/plain"


@dataclass
class MCPResourceContent:
    """Content of an MCP resource."""

    uri: str
    mime_type: str = "text/plain"
    text: str = ""


@dataclass
class MCPPrompt:
    """An MCP prompt template."""

    name: str
    description: str = ""
    arguments: list[dict] = field(default_factory=list)  # [{"name", "description", "required"}]


@dataclass
class MCPPromptResult:
    """Result of rendering a prompt template."""

    description: str = ""
    messages: list[dict] = field(default_factory=list)  # [{"role": "user", "content": {...}}]
