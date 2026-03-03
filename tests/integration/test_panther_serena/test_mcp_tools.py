"""Tests for panther-serena MCP tool schema validation.

Validates that the MCP server exposes the expected Ivy-specific and standard
Serena tools with correct parameter schemas.
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_mcp,
]


class TestIvyToolsExist:
    """Verify Ivy-specific MCP tools are registered."""

    def test_ivy_check_tool_exists(self, mcp_tool_names):
        assert (
            "ivy_check" in mcp_tool_names
        ), f"ivy_check not found in tools: {sorted(mcp_tool_names)}"

    def test_ivy_compile_tool_exists(self, mcp_tool_names):
        assert (
            "ivy_compile" in mcp_tool_names
        ), f"ivy_compile not found in tools: {sorted(mcp_tool_names)}"

    def test_ivy_model_info_tool_exists(self, mcp_tool_names):
        assert (
            "ivy_model_info" in mcp_tool_names
        ), f"ivy_model_info not found in tools: {sorted(mcp_tool_names)}"


class TestIvyToolSchemas:
    """Verify Ivy tool parameter schemas are well-formed."""

    def test_ivy_check_has_file_path_param(self, mcp_server):
        tool = mcp_server.get_tool("ivy_check")
        if tool is None:
            pytest.skip("ivy_check tool not available")
        schema = tool.get("inputSchema", {})
        properties = schema.get("properties", {})
        assert (
            "file_path" in properties
        ), f"ivy_check missing file_path param. Schema: {schema}"

    def test_ivy_compile_has_file_path_param(self, mcp_server):
        tool = mcp_server.get_tool("ivy_compile")
        if tool is None:
            pytest.skip("ivy_compile tool not available")
        schema = tool.get("inputSchema", {})
        properties = schema.get("properties", {})
        assert (
            "file_path" in properties
        ), f"ivy_compile missing file_path param. Schema: {schema}"

    def test_ivy_compile_has_target_param(self, mcp_server):
        tool = mcp_server.get_tool("ivy_compile")
        if tool is None:
            pytest.skip("ivy_compile tool not available")
        schema = tool.get("inputSchema", {})
        properties = schema.get("properties", {})
        assert (
            "target" in properties
        ), f"ivy_compile missing target param. Schema: {schema}"

    def test_ivy_model_info_has_file_path_param(self, mcp_server):
        tool = mcp_server.get_tool("ivy_model_info")
        if tool is None:
            pytest.skip("ivy_model_info tool not available")
        schema = tool.get("inputSchema", {})
        properties = schema.get("properties", {})
        assert (
            "file_path" in properties
        ), f"ivy_model_info missing file_path param. Schema: {schema}"

    def test_ivy_check_schema_is_object_type(self, mcp_server):
        tool = mcp_server.get_tool("ivy_check")
        if tool is None:
            pytest.skip("ivy_check tool not available")
        schema = tool.get("inputSchema", {})
        assert (
            schema.get("type") == "object"
        ), f"ivy_check schema type should be 'object', got: {schema.get('type')}"


class TestStandardSerenaTools:
    """Verify standard Serena tools are available alongside Ivy tools."""

    def test_find_symbol_exists(self, mcp_tool_names):
        assert (
            "find_symbol" in mcp_tool_names
        ), "find_symbol missing from panther-serena tools"

    def test_get_symbols_overview_exists(self, mcp_tool_names):
        assert (
            "get_symbols_overview" in mcp_tool_names
        ), "get_symbols_overview missing from panther-serena tools"

    def test_search_for_pattern_exists(self, mcp_tool_names):
        assert (
            "search_for_pattern" in mcp_tool_names
        ), "search_for_pattern missing from panther-serena tools"

    def test_list_dir_exists(self, mcp_tool_names):
        assert (
            "list_dir" in mcp_tool_names
        ), "list_dir missing from panther-serena tools"

    def test_find_file_exists(self, mcp_tool_names):
        assert (
            "find_file" in mcp_tool_names
        ), "find_file missing from panther-serena tools"


class TestToolCount:
    """Sanity checks on the total number of tools."""

    def test_minimum_tool_count(self, mcp_tools):
        # panther-serena should have standard Serena tools + 3 Ivy tools
        assert len(mcp_tools) >= 10, f"Expected at least 10 tools, got {len(mcp_tools)}"

    def test_all_tools_have_names(self, mcp_tools):
        for tool in mcp_tools:
            assert "name" in tool, f"Tool missing 'name' field: {tool}"
            assert isinstance(
                tool["name"], str
            ), f"Tool name should be str: {tool['name']}"

    def test_all_tools_have_descriptions(self, mcp_tools):
        for tool in mcp_tools:
            assert (
                "description" in tool
            ), f"Tool {tool.get('name', '?')} missing description"
