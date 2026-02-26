"""Shared fixtures for panther-serena MCP integration tests.

Provides an MCP server session fixture that starts panther-serena via stdio
transport and exposes a JSON-RPC client for tool invocations.

Set PANTHER_SERENA_LOCAL=/path/to/local/clone for local development testing.
Set MCP_STARTUP_TIMEOUT=N (default 30) to adjust server startup timeout.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

PANTHER_SERENA_LOCAL = os.environ.get("PANTHER_SERENA_LOCAL")
MCP_STARTUP_TIMEOUT = int(os.environ.get("MCP_STARTUP_TIMEOUT", "30"))


class MCPClient:
    """Minimal JSON-RPC client for MCP server over stdio."""

    def __init__(self, process: subprocess.Popen[str]) -> None:
        self._process = process
        self._request_id = 0
        self._tools: list[dict] | None = None

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send(self, message: dict) -> None:
        """Send a JSON-RPC message to the server's stdin."""
        if not self.is_alive:
            raise RuntimeError(
                f"MCP server process has terminated " f"(rc={self._process.returncode})"
            )
        assert self._process.stdin is not None
        data = json.dumps(message) + "\n"
        self._process.stdin.write(data)
        self._process.stdin.flush()

    def _read_response(self, timeout: float = 10.0) -> dict | None:
        """Read a JSON-RPC response from stdout.

        Handles both newline-delimited JSON and Content-Length framing.
        Returns None on timeout. Logs diagnostics for parse failures.
        """
        import select
        import sys

        assert self._process.stdout is not None
        stdout = self._process.stdout
        start = time.monotonic()

        while time.monotonic() - start < timeout:
            if hasattr(stdout, "fileno"):
                try:
                    ready, _, _ = select.select([stdout], [], [], 0.5)
                    if not ready:
                        continue
                except (ValueError, OSError):
                    if self._process.poll() is not None:
                        print(
                            f"[MCPClient] Server process exited "
                            f"(rc={self._process.returncode})",
                            file=sys.stderr,
                        )
                        return None
                    time.sleep(0.1)
                    continue

            line = stdout.readline()
            if not line:
                if self._process.poll() is not None:
                    return None
                time.sleep(0.1)
                continue

            line = line.strip()
            if not line:
                continue

            if line.startswith("Content-Length:"):
                try:
                    length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    print(
                        f"[MCPClient] Bad Content-Length: {line!r}",
                        file=sys.stderr,
                    )
                    continue
                stdout.readline()  # blank separator
                content = stdout.read(length)
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    print(
                        f"[MCPClient] Malformed JSON after Content-Length: "
                        f"{content[:200]!r}",
                        file=sys.stderr,
                    )
                    continue
            else:
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    # Non-JSON line (server log, banner, etc.) -- skip
                    continue

        return None

    def _read_all_responses(self, timeout: float = 5.0) -> list[dict]:
        """Read all available responses within timeout."""
        responses = []
        while True:
            resp = self._read_response(timeout=timeout)
            if resp is None:
                break
            responses.append(resp)
            # Reduce timeout for subsequent reads
            timeout = 1.0
        return responses

    def initialize(self) -> dict | None:
        """Send initialize handshake."""
        self._send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "panther-test", "version": "1.0.0"},
                },
            }
        )

        response = self._read_response(timeout=MCP_STARTUP_TIMEOUT)

        # Send initialized notification
        self._send(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }
        )

        return response

    def list_tools(self) -> list[dict]:  # type: ignore[type-arg]
        """Request tools/list and return tool definitions."""
        cached = self._tools
        if cached is not None:
            return cached

        self._send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list",
                "params": {},
            }
        )

        response = self._read_response(timeout=15.0)
        if response is None:
            return []
        if "error" in response:
            import sys

            print(
                f"[MCPClient] tools/list error: {response['error']}",
                file=sys.stderr,
            )
            return []
        tools: list[dict] = response.get("result", {}).get("tools", [])
        self._tools = tools
        return tools

    def call_tool(self, name: str, arguments: dict | None = None) -> dict | None:
        """Invoke a tool by name with the given arguments."""
        self._send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments or {},
                },
            }
        )
        return self._read_response(timeout=30.0)

    def get_tool(self, name: str) -> dict | None:
        """Find a tool definition by name."""
        tools = self.list_tools()
        for tool in tools:
            if tool.get("name") == name:
                return tool
        return None

    @property
    def is_alive(self) -> bool:
        return self._process.poll() is None


@pytest.fixture(scope="session")
def mcp_server(tmp_path_factory):
    """Start panther-serena MCP server via stdio, yield MCPClient, kill on teardown."""
    if PANTHER_SERENA_LOCAL:
        cmd = ["uvx", "--from", PANTHER_SERENA_LOCAL, "serena", "run"]
    else:
        cmd = [
            "uvx",
            "--from",
            "git+https://github.com/ElNiak/panther-serena",
            "serena",
            "run",
        ]

    # Redirect stderr to file to prevent pipe buffer deadlock
    stderr_log = tmp_path_factory.mktemp("mcp") / "stderr.log"
    stderr_file = open(stderr_log, "w")

    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        stderr_file.close()
        pytest.skip("uvx not found - cannot start panther-serena MCP server")

    time.sleep(2)

    if process.poll() is not None:
        stderr_file.close()
        stderr_content = stderr_log.read_text()[:500]
        pytest.skip(f"panther-serena MCP server failed to start: {stderr_content}")

    client = MCPClient(process)

    init_response = client.initialize()
    if init_response is None:
        try:
            process.kill()
            process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass
        stderr_file.close()
        pytest.skip("panther-serena MCP server did not respond to initialize")

    yield client

    # Teardown
    try:
        process.kill()
        process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        pass
    stderr_file.close()


@pytest.fixture(scope="session")
def mcp_tools(mcp_server):
    """List of tool definitions from the MCP server."""
    tools = mcp_server.list_tools()
    if not tools:
        pytest.skip("No tools returned from panther-serena MCP server")
    return tools


@pytest.fixture(scope="session")
def mcp_tool_names(mcp_tools) -> set[str]:
    """Set of tool names available from the MCP server."""
    return {t["name"] for t in mcp_tools}


@pytest.fixture
def ivy_spec_dir():
    """Path to an Ivy spec directory in the panther_ivy submodule (prefers QUIC, falls back to APT/minip)."""
    base = Path(__file__).parents[3]
    candidates = [
        base
        / "panther"
        / "plugins"
        / "services"
        / "testers"
        / "panther_ivy"
        / "protocol-testing"
        / "quic"
        / "quic_stack",
        base
        / "panther"
        / "plugins"
        / "services"
        / "testers"
        / "panther_ivy"
        / "protocol-testing"
        / "apt"
        / "apt_protocols"
        / "minip"
        / "minip_stack",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    pytest.skip("panther_ivy submodule not available or no Ivy specs found")


@pytest.fixture
def ivy_spec_path(ivy_spec_dir):
    """Path to a single known .ivy spec file for testing."""
    ivy_files = list(ivy_spec_dir.glob("*.ivy"))
    if not ivy_files:
        pytest.skip(f"No .ivy files found in {ivy_spec_dir}")
    return ivy_files[0]


@pytest.fixture
def ivy_type_spec_path():
    """Path to a type-definition .ivy file for tests that need a lightweight spec."""
    base = Path(__file__).parents[3]
    candidates = [
        base
        / "panther"
        / "plugins"
        / "services"
        / "testers"
        / "panther_ivy"
        / "protocol-testing"
        / "apt"
        / "apt_protocols"
        / "minip"
        / "minip_stack"
        / "ping_types.ivy",
        base
        / "panther"
        / "plugins"
        / "services"
        / "testers"
        / "panther_ivy"
        / "protocol-testing"
        / "quic"
        / "quic_utils"
        / "quic_types.ivy",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    pytest.skip("No type definition .ivy files found in submodule")
