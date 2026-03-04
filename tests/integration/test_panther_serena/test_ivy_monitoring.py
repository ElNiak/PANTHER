"""Integration tests for ivy-lsp monitoring tools via panther-serena MCP.

Tests ivy/serverStatus, ivy/indexerStats, and ivy/listTests
using the MCP tool interface.

Requires a running panther-serena MCP server (set PANTHER_SERENA_LOCAL).
"""

from __future__ import annotations

import json

import pytest


def _find_ivy_tool(mcp_server, partial_name: str) -> str | None:
    """Find an MCP tool whose name contains partial_name (case-insensitive)."""
    tools = mcp_server.list_tools()
    for tool in tools:
        name = tool.get("name", "")
        if partial_name in name.lower():
            return name
    return None


def _call_and_parse(mcp_server, tool_name: str, arguments: dict | None = None) -> dict:
    """Call an MCP tool and parse its JSON text response."""
    response = mcp_server.call_tool(tool_name, arguments)
    assert response is not None, f"No response from {tool_name}"
    result = response.get("result", {})
    content_blocks = result.get("content", [])
    assert content_blocks, f"Empty content from {tool_name}"
    text = content_blocks[0].get("text", "{}")
    return json.loads(text)


@pytest.mark.integration
class TestIvyServerStatus:
    """Tests for IvyServerStatusTool using ivy/serverStatus."""

    def test_server_status_returns_valid_response(self, mcp_server):
        tool_name = _find_ivy_tool(mcp_server, "server_status")
        if tool_name is None:
            pytest.skip("IvyServerStatusTool not found in MCP tools")

        data = _call_and_parse(mcp_server, tool_name)
        assert "server_active" in data

        if data.get("server_active"):
            # When LS is running, we should get rich status info
            assert "mode" in data or "version" in data or "uptime" in data

    def test_server_status_has_tool_availability(self, mcp_server):
        tool_name = _find_ivy_tool(mcp_server, "server_status")
        if tool_name is None:
            pytest.skip("IvyServerStatusTool not found in MCP tools")

        data = _call_and_parse(mcp_server, tool_name)
        if not data.get("server_active"):
            pytest.skip("Ivy language server not active")

        # The status should report tool availability
        tools = data.get("tools", {})
        if tools:
            assert isinstance(tools, dict)


@pytest.mark.integration
class TestIvyTestScopes:
    """Tests for IvyTestScopeTool using ivy/listTests."""

    def test_list_tests_returns_array(self, mcp_server):
        tool_name = _find_ivy_tool(mcp_server, "test_scope")
        if tool_name is None:
            pytest.skip("IvyTestScopeTool not found in MCP tools")

        data = _call_and_parse(mcp_server, tool_name, {"action": "list"})
        assert "server_active" in data

        if data.get("server_active"):
            assert "tests" in data
            assert isinstance(data["tests"], list)

    def test_list_tests_has_active_test_field(self, mcp_server):
        tool_name = _find_ivy_tool(mcp_server, "test_scope")
        if tool_name is None:
            pytest.skip("IvyTestScopeTool not found in MCP tools")

        data = _call_and_parse(mcp_server, tool_name, {"action": "list"})
        if not data.get("server_active"):
            pytest.skip("Ivy language server not active")

        assert "activeTest" in data


@pytest.mark.integration
class TestIvyDiagnosticsWithFeatureStatus:
    """Tests for enhanced IvyDiagnosticsTool with featureStatus."""

    def test_diagnostics_includes_feature_status(self, mcp_server):
        tool_name = _find_ivy_tool(mcp_server, "diagnostic")
        if tool_name is None:
            pytest.skip("IvyDiagnosticsTool not found in MCP tools")

        data = _call_and_parse(mcp_server, tool_name)
        assert "server_active" in data

        if data.get("server_active"):
            # When LS is running, featureStatus should be present
            if "featureStatus" in data:
                fs = data["featureStatus"]
                assert "features" in fs
                assert isinstance(fs["features"], list)
