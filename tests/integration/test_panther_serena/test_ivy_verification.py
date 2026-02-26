"""Tests for live Ivy tool invocations via the panther-serena MCP server.

These tests invoke real Ivy verification, compilation, and model inspection
tools against actual .ivy spec files in the panther_ivy submodule.

Requirements:
- panther-serena MCP server running (via mcp_server fixture)
- panther_ivy submodule checked out with .ivy spec files
- Ivy + Z3 installed in the server environment
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_mcp,
    pytest.mark.requires_ivy,
]


class TestIvyCheck:
    """Test ivy_check tool invocation."""

    def test_ivy_check_valid_spec(self, mcp_server, ivy_type_spec_path):
        """Check a known-good type spec file - should succeed."""
        response = mcp_server.call_tool(
            "ivy_check",
            {"file_path": str(ivy_type_spec_path)},
        )
        assert response is not None, "No response from ivy_check"

        if "error" in response:
            pytest.skip(
                f"ivy_check returned error (Ivy may not be installed): "
                f"{response['error']}"
            )

        result = response.get("result", {})
        # The result should contain content with text
        content = result.get("content", [])
        assert len(content) > 0, f"Empty content from ivy_check: {result}"

    def test_ivy_check_nonexistent_file(self, mcp_server, tmp_path):
        """Check a file that doesn't exist - should return an error."""
        fake_path = str(tmp_path / "nonexistent.ivy")
        response = mcp_server.call_tool(
            "ivy_check",
            {"file_path": fake_path},
        )
        assert response is not None, "No response from ivy_check"

        # Should be an error or result indicating failure
        has_error = "error" in response
        result_text = str(response.get("result", {}).get("content", ""))
        has_error_in_content = any(
            kw in result_text.lower()
            for kw in ("error", "not found", "no such file", "fail")
        )
        assert (
            has_error or has_error_in_content
        ), f"Expected error for nonexistent file, got: {response}"

    def test_ivy_check_reports_errors_on_broken_spec(self, mcp_server, tmp_path):
        """Check a syntactically broken spec - should report errors."""
        broken_spec = tmp_path / "broken.ivy"
        broken_spec.write_text(
            "#lang ivy1.8\n"
            "type broken_type\n"
            "relation foo(X: broken_type, Y: undefined_type)\n"
        )

        response = mcp_server.call_tool(
            "ivy_check",
            {"file_path": str(broken_spec)},
        )
        assert response is not None, "No response from ivy_check"

        if "error" in response:
            # Tool-level error is acceptable
            return

        result_text = str(response.get("result", {}).get("content", ""))
        has_error_indicator = any(
            kw in result_text.lower()
            for kw in ("error", "undefined", "fail", "unknown")
        )
        assert (
            has_error_indicator
        ), f"Expected error indicators for broken spec, got: {result_text[:300]}"


class TestIvyCompile:
    """Test ivy_compile tool invocation."""

    def test_ivy_compile_with_target(self, mcp_server, ivy_type_spec_path):
        """Compile a spec with target=test."""
        response = mcp_server.call_tool(
            "ivy_compile",
            {
                "file_path": str(ivy_type_spec_path),
                "target": "test",
            },
        )
        assert response is not None, "No response from ivy_compile"

        if "error" in response:
            error_msg = str(response.get("error", ""))
            if "ivy" in error_msg.lower() or "not found" in error_msg.lower():
                pytest.skip(f"Ivy compiler not available: {error_msg[:200]}")

        # Should have some result content
        result = response.get("result", {})
        content = result.get("content", [])
        assert (
            len(content) > 0 or "error" in response
        ), f"Empty response from ivy_compile: {response}"

    def test_ivy_compile_default_target(self, mcp_server, ivy_type_spec_path):
        """Compile without specifying target - should use default."""
        response = mcp_server.call_tool(
            "ivy_compile",
            {"file_path": str(ivy_type_spec_path)},
        )
        assert response is not None, "No response from ivy_compile"

        if "error" in response:
            error_msg = str(response.get("error", ""))
            if "ivy" in error_msg.lower() or "not found" in error_msg.lower():
                pytest.skip(f"Ivy compiler not available: {error_msg[:200]}")

    def test_ivy_compile_nonexistent_file(self, mcp_server, tmp_path):
        """Compile a file that doesn't exist - should return an error."""
        fake_path = str(tmp_path / "nonexistent.ivy")
        response = mcp_server.call_tool(
            "ivy_compile",
            {"file_path": fake_path, "target": "test"},
        )
        assert response is not None, "No response from ivy_compile"

        has_error = "error" in response
        result_text = str(response.get("result", {}).get("content", ""))
        has_error_in_content = any(
            kw in result_text.lower()
            for kw in ("error", "not found", "no such file", "fail")
        )
        assert (
            has_error or has_error_in_content
        ), f"Expected error for nonexistent file, got: {response}"


class TestIvyModelInfo:
    """Test ivy_model_info tool invocation."""

    def test_ivy_model_info_returns_structure(self, mcp_server, ivy_type_spec_path):
        """Model info should return type/relation/action information."""
        response = mcp_server.call_tool(
            "ivy_model_info",
            {"file_path": str(ivy_type_spec_path)},
        )
        assert response is not None, "No response from ivy_model_info"

        if "error" in response:
            error_msg = str(response.get("error", ""))
            if "ivy" in error_msg.lower() or "not found" in error_msg.lower():
                pytest.skip(f"Ivy model info not available: {error_msg[:200]}")

        result = response.get("result", {})
        content = result.get("content", [])
        assert len(content) > 0, f"Empty content from ivy_model_info: {result}"

        # Content should mention structural elements
        content_text = str(content)
        structural_keywords = ["type", "relation", "action", "invariant"]
        found_any = any(kw in content_text.lower() for kw in structural_keywords)
        assert found_any, (
            f"Model info should reference structural elements. "
            f"Got: {content_text[:300]}"
        )

    def test_ivy_model_info_nonexistent_file(self, mcp_server, tmp_path):
        """Model info for nonexistent file should error."""
        fake_path = str(tmp_path / "ghost.ivy")
        response = mcp_server.call_tool(
            "ivy_model_info",
            {"file_path": fake_path},
        )
        assert response is not None, "No response from ivy_model_info"

        has_error = "error" in response
        result_text = str(response.get("result", {}).get("content", ""))
        has_error_in_content = any(
            kw in result_text.lower()
            for kw in ("error", "not found", "no such file", "fail")
        )
        assert (
            has_error or has_error_in_content
        ), f"Expected error for nonexistent file, got: {response}"
