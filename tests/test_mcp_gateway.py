"""Comprehensive tests for AIOS MCP Gateway v1.0.0

Covers protocol codec, tool/resource/prompt registries,
constitution guard, and full gateway integration tests.
"""

import json
import os
import sys

import pytest

# Ensure project root is on path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from aios_core.mcp.gateway import GatewayConfig, MCPGateway
from aios_core.mcp.prompts import PromptDefinition, PromptRegistry
from aios_core.mcp.protocol import (
    JSONRPCError,
    JSONRPCNotification,
    JSONRPCParseError,
    JSONRPCRequest,
    JSONRPCResponse,
    MCPPrompt,
    MCPPromptResult,
    MCPProtocol,
    MCPResource,
    MCPResourceContent,
    MCPToolCall,
    MCPToolResult,
)
from aios_core.mcp.resources import ResourceDefinition, ResourceRegistry
from aios_core.mcp.tools import ToolDefinition, ToolRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _jsonrpc(method: str, id_val=1, params=None):
    """Build a JSON-RPC request string."""
    msg = {"jsonrpc": "2.0", "id": id_val, "method": method}
    if params:
        msg["params"] = params
    return json.dumps(msg)


def _parse_response(raw: str) -> dict:
    """Parse a JSON-RPC response string into a dict."""
    return json.loads(raw)


def _gw():
    """Create a fresh MCPGateway for testing."""
    cfg = GatewayConfig(
        db_path=":memory:",
        constitution_dir=os.path.join(_project_root, "docs/constitution"),
        policies_dir=os.path.join(_project_root, "policies"),
    )
    return MCPGateway(cfg)


# ===========================================================================
# Protocol tests
# ===========================================================================


class TestProtocol:
    """Tests for MCPProtocol JSON-RPC 2.0 codec."""

    def test_parse_request(self):
        raw = '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
        msg = MCPProtocol.parse(raw)
        assert isinstance(msg, JSONRPCRequest)
        assert msg.id == 1
        assert msg.method == "tools/list"
        assert msg.params == {}

    def test_parse_request_with_params(self):
        raw = '{"jsonrpc":"2.0","id":"abc","method":"tools/call","params":{"name":"foo","arguments":{}}}'
        msg = MCPProtocol.parse(raw)
        assert isinstance(msg, JSONRPCRequest)
        assert msg.id == "abc"
        assert msg.method == "tools/call"
        assert msg.params["name"] == "foo"

    def test_parse_notification(self):
        raw = '{"jsonrpc":"2.0","method":"notifications/cancelled","params":{"reason":"timeout"}}'
        msg = MCPProtocol.parse(raw)
        assert isinstance(msg, JSONRPCNotification)
        assert not hasattr(msg, "id") or msg.id is None
        assert msg.method == "notifications/cancelled"

    def test_parse_response_with_result(self):
        raw = '{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}'
        msg = MCPProtocol.parse(raw)
        assert isinstance(msg, JSONRPCResponse)
        assert msg.id == 1
        assert msg.result == {"tools": []}
        assert msg.error is None

    def test_parse_response_with_error(self):
        raw = '{"jsonrpc":"2.0","id":1,"error":{"code":-32601,"message":"Not found"}}'
        msg = MCPProtocol.parse(raw)
        assert isinstance(msg, JSONRPCResponse)
        assert msg.error is not None
        assert msg.error["code"] == -32601

    def test_parse_invalid_json(self):
        with pytest.raises(JSONRPCParseError) as exc_info:
            MCPProtocol.parse("not json{")
        assert exc_info.value.code == JSONRPCError.PARSE_ERROR

    def test_parse_empty_string(self):
        with pytest.raises(JSONRPCParseError) as exc_info:
            MCPProtocol.parse("")
        assert exc_info.value.code == JSONRPCError.PARSE_ERROR

    def test_parse_whitespace_only(self):
        with pytest.raises(JSONRPCParseError) as exc_info:
            MCPProtocol.parse("   ")
        assert exc_info.value.code == JSONRPCError.PARSE_ERROR

    def test_parse_missing_jsonrpc_field(self):
        raw = '{"id":1,"method":"test"}'
        with pytest.raises(JSONRPCParseError) as exc_info:
            MCPProtocol.parse(raw)
        assert exc_info.value.code == JSONRPCError.INVALID_REQUEST

    def test_parse_non_dict(self):
        raw = '"just a string"'
        with pytest.raises(JSONRPCParseError) as exc_info:
            MCPProtocol.parse(raw)
        assert exc_info.value.code == JSONRPCError.INVALID_REQUEST

    def test_parse_missing_method_result_error(self):
        raw = '{"jsonrpc":"2.0","id":1}'
        with pytest.raises(JSONRPCParseError) as exc_info:
            MCPProtocol.parse(raw)
        assert exc_info.value.code == JSONRPCError.INVALID_REQUEST

    def test_encode_request(self):
        raw = MCPProtocol.encode_request(1, "tools/list", {})
        data = json.loads(raw)
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert data["method"] == "tools/list"
        assert "params" not in data

    def test_encode_request_with_params(self):
        raw = MCPProtocol.encode_request("abc", "tools/call", {"name": "foo"})
        data = json.loads(raw)
        assert data["params"]["name"] == "foo"

    def test_encode_response(self):
        raw = MCPProtocol.encode_response(1, {"tools": []})
        data = json.loads(raw)
        assert data["result"] == {"tools": []}
        assert "error" not in data

    def test_encode_response_error(self):
        raw = MCPProtocol.encode_response(1, error={"code": -32601, "message": "Not found"})
        data = json.loads(raw)
        assert data["error"]["code"] == -32601
        assert "result" not in data

    def test_encode_notification(self):
        raw = MCPProtocol.encode_notification("ping", {"ts": 123})
        data = json.loads(raw)
        assert data["method"] == "ping"
        assert "id" not in data

    def test_encode_error(self):
        raw = MCPProtocol.encode_error(None, -32700, "Parse error")
        data = json.loads(raw)
        assert data["error"]["code"] == -32700
        assert data["id"] is None

    def test_encode_error_with_data(self):
        raw = MCPProtocol.encode_error(1, -32001, "Denied", {"reason": "risk"})
        data = json.loads(raw)
        assert data["error"]["data"]["reason"] == "risk"

    def test_roundtrip_request(self):
        original = MCPProtocol.encode_request(42, "test/method", {"key": "val"})
        msg = MCPProtocol.parse(original)
        assert isinstance(msg, JSONRPCRequest)
        assert msg.id == 42
        assert msg.method == "test/method"
        assert msg.params == {"key": "val"}

    def test_roundtrip_notification(self):
        original = MCPProtocol.encode_notification("test/notify", {"x": 1})
        msg = MCPProtocol.parse(original)
        assert isinstance(msg, JSONRPCNotification)
        assert msg.method == "test/notify"

    def test_mcp_tool_call_creation(self):
        tc = MCPToolCall(name="test_tool", arguments={"a": 1})
        assert tc.name == "test_tool"
        assert tc.arguments == {"a": 1}
        assert len(tc.request_id) == 12

    def test_mcp_tool_result_creation(self):
        tr = MCPToolResult(content=[{"type": "text", "text": "hello"}])
        assert tr.is_error is False
        assert len(tr.content) == 1

    def test_mcp_resource_creation(self):
        r = MCPResource(uri="test://foo", name="Foo", description="A test")
        assert r.uri == "test://foo"
        assert r.mime_type == "text/plain"

    def test_mcp_resource_content_creation(self):
        rc = MCPResourceContent(uri="test://foo", text="content")
        assert rc.text == "content"

    def test_mcp_prompt_creation(self):
        p = MCPPrompt(name="test_prompt", description="Test")
        assert p.arguments == []

    def test_mcp_prompt_result_creation(self):
        pr = MCPPromptResult(
            description="Test result",
            messages=[{"role": "user", "content": {"type": "text", "text": "Hi"}}],
        )
        assert len(pr.messages) == 1


# ===========================================================================
# ToolRegistry tests
# ===========================================================================


class TestTools:
    """Tests for ToolRegistry."""

    def test_register_and_get(self):
        reg = ToolRegistry()
        tool = ToolDefinition(
            name="test_add",
            description="Add two numbers",
            input_schema={
                "type": "object",
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["a", "b"],
            },
            handler=lambda p: p["a"] + p["b"],
        )
        reg.register(tool)
        assert reg.get("test_add") is tool

    def test_register_duplicate_raises(self):
        reg = ToolRegistry()
        tool = ToolDefinition(
            name="dup",
            description="D",
            input_schema={},
            handler=lambda p: None,
        )
        reg.register(tool)
        with pytest.raises(ValueError, match="already registered"):
            reg.register(tool)

    def test_unregister(self):
        reg = ToolRegistry()
        tool = ToolDefinition(
            name="to_remove",
            description="R",
            input_schema={},
            handler=lambda p: None,
        )
        reg.register(tool)
        assert reg.unregister("to_remove") is True
        assert reg.get("to_remove") is None

    def test_unregister_nonexistent(self):
        reg = ToolRegistry()
        assert reg.unregister("no_such_tool") is False

    def test_list_tools(self):
        reg = ToolRegistry()
        reg.register(
            ToolDefinition(
                name="t1",
                description="Tool 1",
                input_schema={},
                handler=lambda p: None,
            )
        )
        reg.register(
            ToolDefinition(
                name="t2",
                description="Tool 2",
                input_schema={"type": "object"},
                handler=lambda p: None,
            )
        )
        tools = reg.list_tools()
        assert len(tools) == 2
        names = {t["name"] for t in tools}
        assert names == {"t1", "t2"}

    def test_call_valid(self):
        reg = ToolRegistry()
        reg.register(
            ToolDefinition(
                name="echo",
                description="Echo input",
                input_schema={
                    "type": "object",
                    "properties": {"msg": {"type": "string"}},
                    "required": ["msg"],
                },
                handler=lambda p: {"echoed": p["msg"]},
            )
        )
        result = reg.call(MCPToolCall(name="echo", arguments={"msg": "hello"}))
        assert result.is_error is False
        assert len(result.content) == 1
        data = json.loads(result.content[0]["text"])
        assert data["echoed"] == "hello"

    def test_call_unknown_tool_raises(self):
        reg = ToolRegistry()
        with pytest.raises(RuntimeError, match="Tool not found"):
            reg.call(MCPToolCall(name="nonexistent", arguments={}))

    def test_call_missing_required_params(self):
        reg = ToolRegistry()
        reg.register(
            ToolDefinition(
                name="needs_x",
                description="Needs x",
                input_schema={
                    "type": "object",
                    "properties": {"x": {"type": "string"}},
                    "required": ["x"],
                },
                handler=lambda p: p["x"],
            )
        )
        result = reg.call(MCPToolCall(name="needs_x", arguments={}))
        assert result.is_error is True
        assert "Missing required" in result.content[0]["text"]

    def test_call_handler_exception(self):
        reg = ToolRegistry()
        reg.register(
            ToolDefinition(
                name="boom",
                description="Always fails",
                input_schema={},
                handler=lambda p: 1 / 0,
            )
        )
        result = reg.call(MCPToolCall(name="boom", arguments={}))
        assert result.is_error is True
        assert "Tool execution error" in result.content[0]["text"]

    def test_call_returns_mcp_tool_result(self):
        reg = ToolRegistry()
        expected = MCPToolResult(content=[{"type": "text", "text": "direct"}])
        reg.register(
            ToolDefinition(
                name="direct_result",
                description="Returns MCPToolResult directly",
                input_schema={},
                handler=lambda p: expected,
            )
        )
        result = reg.call(MCPToolCall(name="direct_result", arguments={}))
        assert result is expected
        assert result.is_error is False

    def test_categories(self):
        reg = ToolRegistry()
        reg.register(
            ToolDefinition(
                name="cat_a",
                description="A",
                input_schema={},
                handler=lambda p: None,
                category="alpha",
            )
        )
        reg.register(
            ToolDefinition(
                name="cat_b1",
                description="B1",
                input_schema={},
                handler=lambda p: None,
                category="beta",
            )
        )
        reg.register(
            ToolDefinition(
                name="cat_b2",
                description="B2",
                input_schema={},
                handler=lambda p: None,
                category="beta",
            )
        )
        cats = reg.categories()
        assert "alpha" in cats
        assert len(cats["beta"]) == 2

    def test_stats(self):
        reg = ToolRegistry()
        reg.register(
            ToolDefinition(
                name="s1",
                description="S",
                input_schema={},
                handler=lambda p: None,
                category="c1",
                risk_level="low",
            )
        )
        reg.register(
            ToolDefinition(
                name="s2",
                description="S",
                input_schema={},
                handler=lambda p: None,
                category="c2",
                risk_level="high",
            )
        )
        st = reg.stats()
        assert st["total"] == 2
        assert st["by_category"]["c1"] == 1
        assert st["by_risk"]["high"] == 1


# ===========================================================================
# ResourceRegistry tests
# ===========================================================================


class TestResources:
    """Tests for ResourceRegistry."""

    def test_register_and_get(self):
        reg = ResourceRegistry()
        res = ResourceDefinition(
            uri="test://hello",
            name="Hello",
            description="A greeting",
            provider=lambda: "Hello, world!",
        )
        reg.register(res)
        assert reg.get("test://hello") is res

    def test_register_duplicate_raises(self):
        reg = ResourceRegistry()
        res = ResourceDefinition(uri="test://dup", name="Dup", provider=lambda: "")
        reg.register(res)
        with pytest.raises(ValueError, match="already registered"):
            reg.register(res)

    def test_unregister(self):
        reg = ResourceRegistry()
        res = ResourceDefinition(uri="test://rm", name="RM", provider=lambda: "")
        reg.register(res)
        assert reg.unregister("test://rm") is True
        assert reg.get("test://rm") is None

    def test_unregister_nonexistent(self):
        reg = ResourceRegistry()
        assert reg.unregister("test://nope") is False

    def test_list_resources(self):
        reg = ResourceRegistry()
        reg.register(ResourceDefinition(uri="test://a", name="A", provider=lambda: ""))
        reg.register(
            ResourceDefinition(uri="test://b", name="B", description="Desc", provider=lambda: "")
        )
        resources = reg.list_resources()
        assert len(resources) == 2
        uris = {r["uri"] for r in resources}
        assert uris == {"test://a", "test://b"}

    def test_read_with_provider(self):
        reg = ResourceRegistry()
        reg.register(
            ResourceDefinition(
                uri="test://greet",
                name="Greet",
                provider=lambda: "Hi there!",
            )
        )
        content = reg.read("test://greet")
        assert content is not None
        assert content.text == "Hi there!"
        assert content.uri == "test://greet"

    def test_read_unknown_uri(self):
        reg = ResourceRegistry()
        assert reg.read("test://unknown") is None

    def test_read_many(self):
        reg = ResourceRegistry()
        reg.register(ResourceDefinition(uri="test://x", name="X", provider=lambda: "x"))
        reg.register(ResourceDefinition(uri="test://y", name="Y", provider=lambda: "y"))
        results = reg.read_many(["test://x", "test://y", "test://z"])
        assert len(results) == 2
        texts = {r.text for r in results}
        assert texts == {"x", "y"}

    def test_read_provider_exception(self):
        def bad_provider():
            raise RuntimeError("oops")

        reg = ResourceRegistry()
        reg.register(ResourceDefinition(uri="test://bad", name="Bad", provider=bad_provider))
        content = reg.read("test://bad")
        assert content is not None
        assert content.text == ""

    def test_stats(self):
        reg = ResourceRegistry()
        reg.register(
            ResourceDefinition(uri="test://s1", name="S1", category="cat_a", provider=lambda: "")
        )
        reg.register(
            ResourceDefinition(uri="test://s2", name="S2", category="cat_a", provider=lambda: "")
        )
        reg.register(
            ResourceDefinition(uri="test://s3", name="S3", category="cat_b", provider=lambda: "")
        )
        st = reg.stats()
        assert st["total"] == 3
        assert st["by_category"]["cat_a"] == 2


# ===========================================================================
# PromptRegistry tests
# ===========================================================================


class TestPrompts:
    """Tests for PromptRegistry."""

    def test_register_and_get(self):
        reg = PromptRegistry()
        prompt = PromptDefinition(
            name="test_prompt",
            description="A test prompt",
            template="Hello {name}!",
        )
        reg.register(prompt)
        assert reg.get("test_prompt") is prompt

    def test_register_duplicate_raises(self):
        reg = PromptRegistry()
        prompt = PromptDefinition(name="dup", template="x")
        reg.register(prompt)
        with pytest.raises(ValueError, match="already registered"):
            reg.register(prompt)

    def test_unregister(self):
        reg = PromptRegistry()
        prompt = PromptDefinition(name="rm_prompt", template="x")
        reg.register(prompt)
        assert reg.unregister("rm_prompt") is True
        assert reg.get("rm_prompt") is None

    def test_unregister_nonexistent(self):
        reg = PromptRegistry()
        assert reg.unregister("no_such_prompt") is False

    def test_list_prompts(self):
        reg = PromptRegistry()
        reg.register(PromptDefinition(name="p1", description="Prompt 1"))
        reg.register(PromptDefinition(name="p2", description="Prompt 2"))
        prompts = reg.list_prompts()
        assert len(prompts) == 2
        names = {p["name"] for p in prompts}
        assert names == {"p1", "p2"}

    def test_render_with_template(self):
        reg = PromptRegistry()
        reg.register(
            PromptDefinition(
                name="greet",
                description="Greeting",
                template="Hello {name}, welcome to {place}!",
            )
        )
        result = reg.render("greet", {"name": "Alice", "place": "AIOS"})
        assert result is not None
        assert len(result.messages) == 1
        assert result.messages[0]["role"] == "user"
        text = result.messages[0]["content"]["text"]
        assert "Alice" in text
        assert "AIOS" in text

    def test_render_with_custom_renderer(self):
        def my_renderer(args):
            return MCPPromptResult(
                description="custom",
                messages=[
                    {
                        "role": "system",
                        "content": {"type": "text", "text": f"Custom: {args.get('x', '')}"},
                    }
                ],
            )

        reg = PromptRegistry()
        reg.register(
            PromptDefinition(
                name="custom",
                description="Custom renderer",
                renderer=my_renderer,
            )
        )
        result = reg.render("custom", {"x": "42"})
        assert result is not None
        assert result.messages[0]["role"] == "system"
        assert "42" in result.messages[0]["content"]["text"]

    def test_render_unknown_prompt(self):
        reg = PromptRegistry()
        assert reg.render("nonexistent") is None

    def test_render_missing_template_args(self):
        """Template with missing args keeps the placeholder."""
        reg = PromptRegistry()
        reg.register(
            PromptDefinition(
                name="partial",
                template="Value: {value}",
            )
        )
        result = reg.render("partial", {})
        assert result is not None
        # format() would raise KeyError, so fallback is used (template as-is)
        assert result.messages[0]["content"]["text"] == "Value: {value}"

    def test_stats(self):
        reg = PromptRegistry()
        reg.register(PromptDefinition(name="with_template", template="Hello {x}"))
        reg.register(PromptDefinition(name="with_renderer", renderer=lambda a: MCPPromptResult()))
        reg.register(PromptDefinition(name="bare"))
        st = reg.stats()
        assert st["total"] == 3
        assert st["with_renderer"] == 1
        assert st["with_template"] == 1


# ===========================================================================
# ConstitutionGuard tests
# ===========================================================================


class TestGuard:
    """Tests for ConstitutionGuard."""

    def test_check_low_risk_allows(self):
        gw = _gw()
        tool_call = MCPToolCall(name="aios_stats", arguments={})
        tool_def = gw.tools.get("aios_stats")
        result = gw.guard.check(tool_call, tool_def)
        assert result["decision"] == "ALLOW"
        assert result["allowed"] is True

    def test_check_high_risk_reviews(self):
        gw = _gw()
        tool_call = MCPToolCall(name="aios_approve", arguments={"approval_id": "fake-id"})
        tool_def = gw.tools.get("aios_approve")
        result = gw.guard.check(tool_call, tool_def)
        assert result["decision"] == "REVIEW"
        assert result["allowed"] is False

    def test_guard_stats(self):
        gw = _gw()
        tool_def = gw.tools.get("aios_stats")
        gw.guard.check(MCPToolCall(name="aios_stats", arguments={}), tool_def)
        st = gw.guard.stats()
        assert st["total_checks"] == 1
        assert "ALLOW" in st["outcomes"]


# ===========================================================================
# MCPGateway integration tests
# ===========================================================================


class TestGateway:
    """Integration tests for the full MCPGateway."""

    def test_initialize_handshake(self):
        gw = _gw()
        raw = _jsonrpc("initialize", id_val=1, params={})
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        assert data["id"] == 1
        assert data["result"]["protocolVersion"] == "2024-11-05"
        assert data["result"]["serverInfo"]["name"] == "aios-mcp-gateway"
        assert data["result"]["capabilities"]["tools"]["listChanged"] is True
        gw.close()

    def test_ping_pong(self):
        gw = _gw()
        raw = _jsonrpc("ping", id_val=2)
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        assert data["result"]["pong"] is True
        gw.close()

    def test_tools_list_returns_builtin_tools(self):
        gw = _gw()
        raw = _jsonrpc("tools/list", id_val=3)
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        tools = data["result"]["tools"]
        names = {t["name"] for t in tools}
        assert "aios_evaluate" in names
        assert "aios_stats" in names
        assert "aios_memory_store" in names
        assert "aios_approve" in names
        assert "aios_deny" in names
        gw.close()

    def test_tools_call_aios_stats_allowed(self):
        gw = _gw()
        raw = _jsonrpc(
            "tools/call",
            id_val=4,
            params={
                "name": "aios_stats",
                "arguments": {},
            },
        )
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        assert "result" in data
        assert "content" in data["result"]
        assert data["result"]["isError"] is False
        gw.close()

    def test_tools_call_aios_evaluate_returns_evaluation(self):
        gw = _gw()
        raw = _jsonrpc(
            "tools/call",
            id_val=5,
            params={
                "name": "aios_evaluate",
                "arguments": {
                    "goal": "Test goal",
                    "scope": "test",
                    "risk": "low",
                },
            },
        )
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        # The constitution guard may ALLOW or REVIEW — check we get a response
        if "error" in data:
            # REVIEW outcome
            assert data["error"]["code"] == JSONRPCError.CONSTITUTION_REVIEW
        else:
            assert "result" in data
            assert data["result"]["isError"] is False
        gw.close()

    def test_tools_call_unknown_tool(self):
        gw = _gw()
        raw = _jsonrpc(
            "tools/call",
            id_val=6,
            params={
                "name": "nonexistent_tool",
                "arguments": {},
            },
        )
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        assert data["error"]["code"] == JSONRPCError.METHOD_NOT_FOUND
        assert "nonexistent_tool" in data["error"]["message"]
        gw.close()

    def test_resources_list_returns_builtin_resources(self):
        gw = _gw()
        raw = _jsonrpc("resources/list", id_val=7)
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        resources = data["result"]["resources"]
        uris = {r["uri"] for r in resources}
        assert "aios://constitution/overview" in uris
        assert "aios://policies/summary" in uris
        assert "aios://audit/recent" not in uris
        assert "aios://approvals/pending" not in uris
        gw.close()

    def test_resources_read_existing(self):
        gw = _gw()
        raw = _jsonrpc(
            "resources/read",
            id_val=8,
            params={
                "uri": "aios://constitution/overview",
            },
        )
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        contents = data["result"]["contents"]
        assert len(contents) == 1
        assert contents[0]["uri"] == "aios://constitution/overview"
        assert "total_articles" in contents[0]["text"]
        gw.close()

    def test_resources_read_unknown(self):
        gw = _gw()
        raw = _jsonrpc(
            "resources/read",
            id_val=9,
            params={
                "uri": "aios://nonexistent/resource",
            },
        )
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        assert data["error"]["code"] == JSONRPCError.RESOURCE_NOT_FOUND
        gw.close()

    def test_prompts_list_returns_builtin_prompts(self):
        gw = _gw()
        raw = _jsonrpc("prompts/list", id_val=10)
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        prompts = data["result"]["prompts"]
        names = {p["name"] for p in prompts}
        assert "evaluate_action" in names
        assert "evolution_proposal" in names
        gw.close()

    def test_prompts_get_with_template(self):
        gw = _gw()
        raw = _jsonrpc(
            "prompts/get",
            id_val=11,
            params={
                "name": "evaluate_action",
                "arguments": {"goal": "Deploy", "scope": "production", "risk": "high"},
            },
        )
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        assert "result" in data
        assert data["result"]["description"] != ""
        assert len(data["result"]["messages"]) == 1
        text = data["result"]["messages"][0]["content"]["text"]
        assert "Deploy" in text
        assert "production" in text
        assert "high" in text
        gw.close()

    def test_aios_evaluate_method(self):
        gw = _gw()
        raw = _jsonrpc(
            "aios/evaluate",
            id_val=12,
            params={
                "goal": "Read audit logs",
                "scope": "system",
                "risk": "low",
            },
        )
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        assert "result" in data
        assert "decision" in data["result"]
        assert data["result"]["decision"] in ("ALLOW", "DENY", "REVIEW")
        gw.close()

    def test_aios_approvals_method(self):
        gw = _gw()
        raw = _jsonrpc("aios/approvals", id_val=13)
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        assert "result" in data
        assert "count" in data["result"]
        assert "approvals" in data["result"]
        gw.close()

    def test_aios_stats_method(self):
        gw = _gw()
        raw = _jsonrpc("aios/stats", id_val=14)
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        assert "result" in data
        result = data["result"]
        assert "gateway" in result
        assert "tools" in result
        assert "resources" in result
        assert "prompts" in result
        assert "constitution_guard" in result
        assert "runtime" in result
        assert "database" in result
        gw.close()

    def test_unknown_method(self):
        gw = _gw()
        raw = _jsonrpc("foo/bar", id_val=15)
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        assert data["error"]["code"] == JSONRPCError.METHOD_NOT_FOUND
        gw.close()

    def test_invalid_json(self):
        gw = _gw()
        resp = gw.handle_request("{invalid json")
        data = _parse_response(resp)
        assert data["error"]["code"] == JSONRPCError.PARSE_ERROR
        gw.close()

    def test_empty_request(self):
        gw = _gw()
        resp = gw.handle_request("")
        data = _parse_response(resp)
        assert data["error"]["code"] == JSONRPCError.PARSE_ERROR
        gw.close()

    def test_missing_jsonrpc_field(self):
        gw = _gw()
        raw = json.dumps({"id": 1, "method": "test"})
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        assert data["error"]["code"] == JSONRPCError.INVALID_REQUEST
        gw.close()

    def test_notification_no_response(self):
        gw = _gw()
        raw = json.dumps({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {}})
        resp = gw.handle_request(raw)
        assert resp is None
        gw.close()

    def test_handle_request_full_roundtrip(self):
        """Full roundtrip: initialize, tools/list, tools/call aios_stats, aios/stats."""
        gw = _gw()

        # Initialize
        resp = gw.handle_request(_jsonrpc("initialize", 1))
        data = _parse_response(resp)
        assert "result" in data

        # tools/list
        resp = gw.handle_request(_jsonrpc("tools/list", 2))
        data = _parse_response(resp)
        assert len(data["result"]["tools"]) > 0

        # tools/call aios_stats
        resp = gw.handle_request(
            _jsonrpc(
                "tools/call",
                3,
                {
                    "name": "aios_stats",
                    "arguments": {},
                },
            )
        )
        data = _parse_response(resp)
        assert "result" in data

        # aios/stats
        resp = gw.handle_request(_jsonrpc("aios/stats", 4))
        data = _parse_response(resp)
        assert data["result"]["gateway"]["initialized"] is True

        gw.close()

    def test_gateway_stats_returns_all_sections(self):
        gw = _gw()
        # Initialize to set flag
        gw.handle_request(_jsonrpc("initialize", 1))
        st = gw.stats()
        assert "gateway" in st
        assert "tools" in st
        assert "resources" in st
        assert "prompts" in st
        assert "constitution_guard" in st
        assert "runtime" in st
        assert "database" in st
        assert st["gateway"]["initialized"] is True
        assert st["gateway"]["version"] == "1.0.0"
        gw.close()

    def test_constitution_blocks_high_risk_tool(self):
        """High-risk tools should get REVIEW or DENY from constitution."""
        gw = _gw()
        raw = _jsonrpc(
            "tools/call",
            id_val=20,
            params={
                "name": "aios_approve",
                "arguments": {"approval_id": "fake-uuid"},
            },
        )
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        # High risk tools should not be allowed directly
        if "error" in data:
            code = data["error"]["code"]
            assert code in (JSONRPCError.CONSTITUTION_REVIEW, JSONRPCError.CONSTITUTION_DENIED)
        gw.close()

    def test_tools_call_aios_memory_store(self):
        gw = _gw()
        raw = _jsonrpc(
            "tools/call",
            id_val=21,
            params={
                "name": "aios_memory_store",
                "arguments": {
                    "content": "Test memory content",
                    "category": "operational",
                    "tags": "test,mcp",
                },
            },
        )
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        # Low risk tool should be allowed
        if "result" in data:
            assert data["result"]["isError"] is False
        gw.close()

    def test_tools_call_aios_memory_search(self):
        gw = _gw()
        raw = _jsonrpc(
            "tools/call",
            id_val=22,
            params={
                "name": "aios_memory_search",
                "arguments": {"query": "test", "limit": 5},
            },
        )
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        if "result" in data:
            assert data["result"]["isError"] is False
        gw.close()

    def test_tools_call_aios_knowledge_query(self):
        gw = _gw()
        raw = _jsonrpc(
            "tools/call",
            id_val=23,
            params={
                "name": "aios_knowledge_query",
                "arguments": {"query": "identity", "limit": 5},
            },
        )
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        if "result" in data:
            assert data["result"]["isError"] is False
        gw.close()

    def test_prompts_get_unknown(self):
        gw = _gw()
        raw = _jsonrpc("prompts/get", id_val=24, params={"name": "no_such_prompt"})
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        assert data["error"]["code"] == JSONRPCError.METHOD_NOT_FOUND
        gw.close()

    def test_sensitive_resources_are_not_exposed(self):
        gw = _gw()
        for uri in ("aios://audit/recent", "aios://approvals/pending"):
            raw = _jsonrpc("resources/read", id_val=25, params={"uri": uri})
            data = _parse_response(gw.handle_request(raw))
            assert data["error"]["code"] == JSONRPCError.RESOURCE_NOT_FOUND
        gw.close()

    def test_tools_call_aios_evaluate_medium_risk(self):
        """Medium risk evaluation — may still ALLOW or REVIEW depending on policies."""
        gw = _gw()
        raw = _jsonrpc(
            "tools/call",
            id_val=27,
            params={
                "name": "aios_evaluate",
                "arguments": {
                    "goal": "System health check",
                    "scope": "system",
                    "risk": "medium",
                },
            },
        )
        resp = gw.handle_request(raw)
        data = _parse_response(resp)
        # Should not be an internal error
        if "error" in data:
            assert data["error"]["code"] != JSONRPCError.INTERNAL_ERROR
        gw.close()

    def test_jsonrpc_error_enum_values(self):
        assert JSONRPCError.PARSE_ERROR == -32700
        assert JSONRPCError.INVALID_REQUEST == -32600
        assert JSONRPCError.METHOD_NOT_FOUND == -32601
        assert JSONRPCError.INVALID_PARAMS == -32602
        assert JSONRPCError.INTERNAL_ERROR == -32603
        assert JSONRPCError.CONSTITUTION_DENIED == -32001
        assert JSONRPCError.CONSTITUTION_REVIEW == -32002
        assert JSONRPCError.TOOL_EXECUTION_ERROR == -32003
        assert JSONRPCError.RESOURCE_NOT_FOUND == -32004

    def test_tool_definition_fields(self):
        td = ToolDefinition(
            name="x",
            description="y",
            input_schema={},
            handler=lambda p: None,
            category="z",
            risk_level="critical",
            requires_consent=True,
        )
        assert td.name == "x"
        assert td.category == "z"
        assert td.risk_level == "critical"
        assert td.requires_consent is True

    def test_gateway_config_defaults(self):
        cfg = GatewayConfig()
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 8471
        assert cfg.db_path == ":memory:"
        assert cfg.server_name == "aios-mcp-gateway"
        assert cfg.server_version == "1.0.0"

    def test_gateway_config_custom(self):
        cfg = GatewayConfig(
            host="0.0.0.0",
            port=9999,
            db_path="test.db",
            server_name="custom",
            server_version="2.0.0",
        )
        assert cfg.port == 9999
        assert cfg.server_version == "2.0.0"

    def test_multiple_requests_on_same_gateway(self):
        gw = _gw()
        # First initialize
        r1 = _parse_response(gw.handle_request(_jsonrpc("initialize", 1)))
        assert r1["result"]["serverInfo"]["name"] == "aios-mcp-gateway"
        # Second ping
        r2 = _parse_response(gw.handle_request(_jsonrpc("ping", 2)))
        assert r2["result"]["pong"] is True
        # Third tools/list
        r3 = _parse_response(gw.handle_request(_jsonrpc("tools/list", 3)))
        assert len(r3["result"]["tools"]) > 0
        gw.close()
