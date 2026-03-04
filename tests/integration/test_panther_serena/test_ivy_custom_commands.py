"""Integration tests for ivy-lsp custom commands via panther-serena tools.

Tests ivy/verify, ivy/compile, ivy/showModel, and ivy/includeGraph
using the MCP tool interface.  Skips if ivy_check / ivyc / ivy_show
are not on PATH.

Requires a running panther-serena MCP server (set PANTHER_SERENA_LOCAL).
"""

from __future__ import annotations

import json
import shutil

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
class TestIvyVerifyCommand:
    """Tests for IvyCheckTool using ivy/verify."""

    @pytest.fixture(autouse=True)
    def _require_ivy_check(self):
        if shutil.which("ivy_check") is None:
            pytest.skip("ivy_check not on PATH")

    def test_verify_valid_file(self, mcp_server, ivy_spec_path):
        tool_name = _find_ivy_tool(mcp_server, "check")
        if tool_name is None:
            pytest.skip("IvyCheckTool not found")

        data = _call_and_parse(
            mcp_server,
            tool_name,
            {"relative_path": str(ivy_spec_path)},
        )
        assert "success" in data
        assert "diagnostic_count" in data or "diagnosticCount" in data

    def test_verify_with_isolate(self, mcp_server, ivy_spec_path):
        tool_name = _find_ivy_tool(mcp_server, "check")
        if tool_name is None:
            pytest.skip("IvyCheckTool not found")

        data = _call_and_parse(
            mcp_server,
            tool_name,
            {"relative_path": str(ivy_spec_path), "isolate": "this"},
        )
        assert "success" in data


@pytest.mark.integration
class TestIvyCompileCommand:
    """Tests for IvyCompileTool using ivy/compile."""

    @pytest.fixture(autouse=True)
    def _require_ivyc(self):
        if shutil.which("ivyc") is None:
            pytest.skip("ivyc not on PATH")

    def test_compile_valid_file(self, mcp_server, ivy_spec_path):
        tool_name = _find_ivy_tool(mcp_server, "compile")
        if tool_name is None:
            pytest.skip("IvyCompileTool not found")

        data = _call_and_parse(
            mcp_server,
            tool_name,
            {"relative_path": str(ivy_spec_path)},
        )
        assert "success" in data or "stdout" in data


@pytest.mark.integration
class TestIvyShowModelCommand:
    """Tests for IvyModelInfoTool using ivy/showModel."""

    @pytest.fixture(autouse=True)
    def _require_ivy_show(self):
        if shutil.which("ivy_show") is None:
            pytest.skip("ivy_show not on PATH")

    def test_show_model_valid_file(self, mcp_server, ivy_spec_path):
        tool_name = _find_ivy_tool(mcp_server, "model")
        if tool_name is None:
            pytest.skip("IvyModelInfoTool not found")

        data = _call_and_parse(
            mcp_server,
            tool_name,
            {"relative_path": str(ivy_spec_path)},
        )
        assert "success" in data or "stdout" in data


@pytest.mark.integration
class TestIvyIncludeGraphCommand:
    """Tests for IvyIncludeGraphTool using ivy/includeGraph."""

    def test_include_graph_full(self, mcp_server):
        tool_name = _find_ivy_tool(mcp_server, "include_graph")
        if tool_name is None:
            pytest.skip("IvyIncludeGraphTool not found")

        data = _call_and_parse(mcp_server, tool_name)
        assert "files" in data or "nodes" in data
        assert "via" in data  # Should report "lsp" or "filesystem"

    def test_include_graph_single_file(self, mcp_server, ivy_spec_path):
        tool_name = _find_ivy_tool(mcp_server, "include_graph")
        if tool_name is None:
            pytest.skip("IvyIncludeGraphTool not found")

        data = _call_and_parse(
            mcp_server,
            tool_name,
            {"relative_path": str(ivy_spec_path)},
        )
        assert "file" in data or "files" in data
