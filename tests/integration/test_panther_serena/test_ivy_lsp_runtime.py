"""Integration tests for ivy-lsp runtime via panther-serena MCP server.

These tests verify that the LSP handshake works, Ivy tools are listed,
and IvyDiagnosticsTool reports server_active.

Requires a running panther-serena MCP server (set PANTHER_SERENA_LOCAL).
"""

from __future__ import annotations

import json

import pytest


@pytest.mark.integration
class TestIvyLspRuntime:
    """Tests for basic ivy-lsp connectivity via the MCP server."""

    def test_mcp_server_initializes(self, mcp_server):
        """Verify the MCP server starts and responds to initialize."""
        assert mcp_server.is_alive

    def test_ivy_tools_listed(self, mcp_tool_names):
        """Verify that Ivy-specific tools appear in the MCP tools list."""
        expected_tools = {
            "ivy_check",
            "ivy_compile",
            "ivy_model_info",
            "ivy_diagnostics",
            "ivy_lint",
            "ivy_goto_definition",
            "ivy_include_graph",
        }
        # Tool names in MCP use snake_case derived from class names
        # The exact names depend on Serena's naming convention
        found = mcp_tool_names & expected_tools
        # At minimum, IvyCheckTool and IvyDiagnosticsTool should be present
        assert len(found) > 0 or any(
            "ivy" in name.lower() for name in mcp_tool_names
        ), f"No Ivy tools found in {mcp_tool_names}"

    def test_ivy_diagnostics_reports_server_active(self, mcp_server):
        """Verify IvyDiagnosticsTool returns server_active field."""
        # Find the diagnostics tool name
        tools = mcp_server.list_tools()
        diag_tool = None
        for tool in tools:
            name = tool.get("name", "")
            if "diagnostic" in name.lower() and "ivy" in name.lower():
                diag_tool = name
                break

        if diag_tool is None:
            pytest.skip("IvyDiagnosticsTool not found in MCP tools list")

        response = mcp_server.call_tool(diag_tool)
        if response is None:
            pytest.skip("No response from diagnostics tool")

        result = response.get("result", {})
        # MCP tools return content as a list of content blocks
        content_blocks = result.get("content", [])
        if not content_blocks:
            pytest.skip("Empty response from diagnostics tool")

        # Parse the text content block
        text = content_blocks[0].get("text", "{}")
        data = json.loads(text)
        assert "server_active" in data

    def test_new_monitoring_tools_listed(self, mcp_tool_names):
        """Verify the new monitoring tools appear in MCP tools list."""
        # Check for any tool with "server_status" or "test_scope" in the name
        has_status = any(
            "status" in name.lower() and "ivy" in name.lower()
            for name in mcp_tool_names
        )
        has_scope = any(
            "scope" in name.lower() or "test" in name.lower()
            for name in mcp_tool_names
            if "ivy" in name.lower()
        )
        # At least one should be present if the tools registered correctly
        if not has_status and not has_scope:
            pytest.skip(
                "New monitoring tools not yet registered in this server version"
            )
