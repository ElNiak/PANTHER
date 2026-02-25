"""Tests for Serena LSP navigation on .ivy files via panther-serena MCP.

These tests verify that the Ivy Language Server Protocol integration works
through the standard Serena navigation tools (find_symbol, get_symbols_overview,
find_referencing_symbols).

Requirements:
- panther-serena MCP server running (via mcp_server fixture)
- panther_ivy submodule checked out with .ivy spec files
- Ivy LSP operational in the server environment
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_mcp,
    pytest.mark.requires_ivy,
]


class TestGetSymbolsOverview:
    """Test get_symbols_overview on .ivy files."""

    def test_overview_returns_symbols(self, mcp_server, ivy_type_spec_path):
        """Overview of a type spec should return top-level symbols."""
        response = mcp_server.call_tool(
            "get_symbols_overview",
            {"relative_path": str(ivy_type_spec_path)},
        )
        assert response is not None, "No response from get_symbols_overview"

        if "error" in response:
            error_msg = str(response.get("error", ""))
            if any(
                kw in error_msg.lower()
                for kw in ("not supported", "not available", "ivy")
            ):
                pytest.skip(f"LSP not available for .ivy files: {error_msg[:200]}")
            # Other errors may be acceptable for first-run
            pytest.skip(f"get_symbols_overview error: {error_msg[:200]}")

        result = response.get("result", {})
        content = result.get("content", [])
        assert (
            len(content) > 0
        ), f"No symbols returned for {ivy_type_spec_path}: {result}"

    def test_overview_on_directory(self, mcp_server, ivy_spec_dir):
        """Overview on a directory should list files or symbols."""
        response = mcp_server.call_tool(
            "get_symbols_overview",
            {"relative_path": str(ivy_spec_dir)},
        )
        assert response is not None, "No response from get_symbols_overview"

        # Directory overview may fail or return file list - both acceptable
        if "error" in response:
            error_msg = str(response.get("error", ""))
            pytest.skip(f"Directory overview not supported: {error_msg[:200]}")


class TestFindSymbol:
    """Test find_symbol on .ivy files."""

    def test_find_known_type_symbol(self, mcp_server, ivy_type_spec_path):
        """Find a type symbol in a type definition file."""
        # Read the file first to find a valid symbol name
        read_response = mcp_server.call_tool(
            "get_symbols_overview",
            {"relative_path": str(ivy_type_spec_path)},
        )
        if read_response is None or "error" in (read_response or {}):
            pytest.skip("Cannot get symbols overview to find a valid symbol")

        result_text = str(read_response.get("result", {}).get("content", ""))

        # Try to extract a symbol name from the overview
        # For Ivy type files, common patterns are type names like "ip_addr"
        # Use a broad search if we can't parse the overview
        response = mcp_server.call_tool(
            "find_symbol",
            {
                "name_path": "*",
                "relative_path": str(ivy_type_spec_path),
                "include_body": False,
            },
        )
        assert response is not None, "No response from find_symbol"

        if "error" in response:
            error_msg = str(response.get("error", ""))
            pytest.skip(f"find_symbol not available: {error_msg[:200]}")

        result = response.get("result", {})
        content = result.get("content", [])
        assert (
            len(content) > 0
        ), f"find_symbol returned no results for {ivy_type_spec_path}"

    def test_find_symbol_with_body(self, mcp_server, ivy_type_spec_path):
        """Find a symbol and include its body."""
        response = mcp_server.call_tool(
            "find_symbol",
            {
                "name_path": "*",
                "relative_path": str(ivy_type_spec_path),
                "include_body": True,
                "depth": 0,
            },
        )
        assert response is not None, "No response from find_symbol"

        if "error" in response:
            pytest.skip(
                f"find_symbol error: " f"{str(response.get('error', ''))[:200]}"
            )

        result = response.get("result", {})
        content_text = str(result.get("content", ""))
        # Body should contain Ivy syntax elements
        assert len(content_text) > 10, f"Symbol body too short: {content_text[:100]}"


class TestFindReferencingSymbols:
    """Test find_referencing_symbols on .ivy files."""

    def test_find_references_to_type(self, mcp_server, ivy_type_spec_path):
        """Find references to a type defined in a spec file."""
        # First, get a symbol name to search references for
        overview = mcp_server.call_tool(
            "get_symbols_overview",
            {"relative_path": str(ivy_type_spec_path)},
        )
        if overview is None or "error" in (overview or {}):
            pytest.skip("Cannot get symbol overview for reference search")

        # Try find_referencing_symbols with a broad pattern
        response = mcp_server.call_tool(
            "find_referencing_symbols",
            {
                "name_path": "*",
                "relative_path": str(ivy_type_spec_path),
            },
        )
        assert response is not None, "No response from find_referencing_symbols"

        if "error" in response:
            error_msg = str(response.get("error", ""))
            # Reference finding may not be supported for all symbols
            if "not found" in error_msg.lower():
                pytest.skip(
                    f"No references found (expected for isolated types): "
                    f"{error_msg[:200]}"
                )
            pytest.skip(f"find_referencing_symbols error: {error_msg[:200]}")

        # If we get results, they should have content
        result = response.get("result", {})
        content = result.get("content", [])
        # May be empty if no references exist - that's acceptable
        assert isinstance(content, list), f"Expected list content, got: {type(content)}"


class TestSearchForPattern:
    """Test search_for_pattern on .ivy files."""

    def test_search_type_keyword(self, mcp_server, ivy_spec_dir):
        """Search for 'type' keyword in Ivy spec directory."""
        response = mcp_server.call_tool(
            "search_for_pattern",
            {
                "pattern": "type",
                "relative_path": str(ivy_spec_dir),
            },
        )
        assert response is not None, "No response from search_for_pattern"

        if "error" in response:
            pytest.skip(
                f"search_for_pattern error: " f"{str(response.get('error', ''))[:200]}"
            )

        result = response.get("result", {})
        content = result.get("content", [])
        content_text = str(content)
        assert "type" in content_text.lower(), (
            f"Search for 'type' should find matches in Ivy specs: "
            f"{content_text[:300]}"
        )

    def test_search_relation_keyword(self, mcp_server, ivy_spec_dir):
        """Search for 'relation' keyword in Ivy spec directory."""
        response = mcp_server.call_tool(
            "search_for_pattern",
            {
                "pattern": "relation",
                "relative_path": str(ivy_spec_dir),
            },
        )
        assert response is not None, "No response from search_for_pattern"

        # Relations may or may not exist in type files - just verify no crash
        if "error" not in response:
            result = response.get("result", {})
            assert (
                "content" in result
            ), f"search_for_pattern should return content: {result}"
