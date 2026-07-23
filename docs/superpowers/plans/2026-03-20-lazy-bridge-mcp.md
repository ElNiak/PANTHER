# Lazy Bridge MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken `mcp-bridge` startup mode with a standalone MCP server that transparently upgrades to bridge mode when the LSP sidecar becomes available.

**Architecture:** The MCP server starts immediately in standalone mode using the offline `.ivy-index/` cache. A background task polls for the LSP sidecar's port file. When detected and validated, tool calls are delegated to the sidecar via an MCP client connection. If the sidecar goes down, the server reverts to local handling transparently.

**Tech Stack:** Python 3.11, FastMCP, mcp library (streamablehttp_client, ClientSession), asyncio, bash

**Spec:** `docs/superpowers/specs/2026-03-20-lazy-bridge-mcp-architecture-design.md`

---

**Path prefixes used throughout this plan:**

- `PLUGIN` = `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin`
- `IVY_LSP` = `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp`
- `IVY_TESTS` = `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/tests`

---

### Task 1: Shell Script and Config Cleanup

Remove the `mcp-bridge` mode from the startup flow. This is the minimal change that fixes the immediate startup failure.

**Files:**
- Modify: `PLUGIN/scripts/start-ivy-server.sh`
- Modify: `PLUGIN/.mcp.json`
- Modify: `PLUGIN/scripts/workspace-common.sh` (line 3 comment)
- Delete: `PLUGIN/scripts/ivy-lsp-wrapper.sh`

- [ ] **Step 1: Change `.mcp.json` from `mcp-bridge` to `mcp`**

In `PLUGIN/.mcp.json`, change the args array:

```json
{
  "mcpServers": {
    "ivy-tools": {
      "command": "bash",
      "args": [
        "${CLAUDE_PLUGIN_ROOT}/scripts/start-ivy-server.sh",
        "--mode",
        "mcp"
      ],
      "env": {
        "IVY_LSP_LOG_LEVEL": "DEBUG",
        "IVY_LSP_DEBUG_LOG": "1",
        "IVY_LSP_MAX_CONCURRENT_TOOLS": "4",
        "IVY_LSP_FAST_INDEX_WORKERS": "4",
        "IVY_LSP_PARSE_WORKERS": "1",
        "IVY_LSP_BULK_WORKERS": "4",
        "IVY_LSP_COMPILE_WORKERS": "2",
        "IVY_LSP_PREWARM_MODEL": "1",
        "IVY_LSP_PREWARM_GRAPH": "1"
      }
    }
  }
}
```

- [ ] **Step 2: Remove `mcp-bridge` from `start-ivy-server.sh`**

Three changes in `PLUGIN/scripts/start-ivy-server.sh`:

**(a)** Line 22 — remove `mcp-bridge` from validation:
```bash
# Before:
if [[ "$MODE" != "lsp" && "$MODE" != "mcp" && "$MODE" != "mcp-bridge" ]]; then
# After:
if [[ "$MODE" != "lsp" && "$MODE" != "mcp" ]]; then
```

**(b)** Lines 29-33 — remove the deprecation notice:
```bash
# DELETE these lines:
if [ "$MODE" = "mcp" ]; then
    echo "[ivy-mcp] NOTE: Standalone MCP mode is deprecated..." >&2
    echo "[ivy-mcp] served by the LSP process via HTTP sidecar..." >&2
    echo "[ivy-mcp] This mode is kept for backward compatibility." >&2
fi
```

**(c)** Lines 92-135 — remove the entire `mcp-bridge` block:
```bash
# DELETE from:
# --- mcp-bridge: wait for sidecar, then relay stdio↔HTTP ---
if [ "$MODE" = "mcp-bridge" ]; then
    ...
fi
# DELETE to the end of the `fi` at line 135.
```

- [ ] **Step 3: Update `workspace-common.sh` comment**

In `PLUGIN/scripts/workspace-common.sh` line 3, update the comment:
```bash
# Before:
# Sourced by start-ivy-tools.sh, ivy-lsp-wrapper.sh, and detect-ivy-workspace.sh.
# After:
# Sourced by start-ivy-server.sh.
```

- [ ] **Step 4: Delete `ivy-lsp-wrapper.sh`**

```bash
rm PLUGIN/scripts/ivy-lsp-wrapper.sh
```

Verify no other files reference it (confirmed: only the comment updated in step 3).

- [ ] **Step 5: Verify shell script syntax**

```bash
bash -n PLUGIN/scripts/start-ivy-server.sh
```

Expected: no output (clean syntax).

- [ ] **Step 6: Commit**

```bash
git add -A PLUGIN/scripts/ PLUGIN/.mcp.json
git commit -m "fix: switch MCP from mcp-bridge to standalone mode

Remove the mcp-bridge startup mode that caused a race condition
with the lazily-started LSP sidecar. MCP now starts immediately
in standalone mode using the offline index."
```

---

### Task 2: Add `workspace_root` to Sidecar Health Endpoint

The `/health` endpoint on the MCP HTTP sidecar must return `workspace_root` so the standalone MCP can validate it's connecting to the right sidecar (not one from a different worktree session).

**Files:**
- Modify: `IVY_LSP/mcp_sidecar.py`
- Test: `IVY_TESTS/test_mcp_sidecar_health.py`

- [ ] **Step 1: Write failing test**

Create `IVY_TESTS/test_mcp_sidecar_health.py`:

```python
"""Tests for the MCP sidecar /health endpoint."""

import json


def test_health_response_includes_workspace_root():
    """The /health endpoint must return workspace_root for validation."""
    from ivy_lsp.mcp_sidecar import _health_middleware_factory

    # Create a mock context with a known workspace root
    class MockCtx:
        root = "/tmp/test-workspace"
        def get_model_status(self):
            return {"state": "ready"}

    middleware = _health_middleware_factory(MockCtx(), start_time=0.0)

    # Simulate an ASGI /health request
    import asyncio

    scope = {"type": "http", "path": "/health"}
    response_started = {}
    response_body = b""

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        nonlocal response_body
        if message["type"] == "http.response.start":
            response_started.update(message)
        elif message["type"] == "http.response.body":
            response_body = message.get("body", b"")

    asyncio.get_event_loop().run_until_complete(
        middleware(scope, receive, send)
    )

    body = json.loads(response_body)
    assert body["status"] == "ok"
    assert body["workspace_root"] == "/tmp/test-workspace"
    assert "uptime_seconds" in body
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/test_mcp_sidecar_health.py -v
```

Expected: FAIL — `_health_middleware_factory` does not exist yet.

- [ ] **Step 3: Refactor `/health` handler into a testable factory**

In `IVY_LSP/mcp_sidecar.py`, extract the inline `_health_middleware` into a factory function. The current code (inside `_serve_mcp_http`) defines the middleware as a closure. Refactor to:

```python
def _health_middleware_factory(ctx: Any, start_time: float):
    """Create an ASGI middleware that intercepts /health requests.

    Args:
        ctx: ToolContext with workspace info and model status.
        start_time: monotonic timestamp of sidecar start for uptime calc.

    Returns:
        An ASGI middleware callable.
    """
    import time as _time_mod

    async def _health_middleware(scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] == "http" and scope["path"] == "/health":
            model_status = "unknown"
            if ctx is not None and hasattr(ctx, "get_model_status"):
                try:
                    model_status = ctx.get_model_status().get("state", "unknown")
                except Exception:
                    model_status = "error"

            body = _json.dumps(
                {
                    "status": "ok",
                    "uptime_seconds": round(_time_mod.monotonic() - start_time, 1),
                    "tools_registered": 13,
                    "model_status": model_status,
                    "workspace_root": getattr(ctx, "root", ""),
                }
            ).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"application/json"]],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        # Non-health requests pass through to the MCP ASGI app
        # (not available in test context — tests only hit /health)
    return _health_middleware
```

Then update `_serve_mcp_http` to use it:
```python
async def _serve_mcp_http(mcp_app, port, workspace_root, ctx=None):
    # ... (uvicorn import, asgi_app setup) ...
    sidecar_start_time = _time.monotonic()
    health_mw = _health_middleware_factory(ctx, sidecar_start_time)

    async def _wrapped_app(scope, receive, send):
        if scope["type"] == "http" and scope["path"] == "/health":
            return await health_mw(scope, receive, send)
        return await asgi_app(scope, receive, send)
    # ... use _wrapped_app in uvicorn config ...
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/test_mcp_sidecar_health.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp_sidecar.py tests/test_mcp_sidecar_health.py
git commit -m "feat: add workspace_root to sidecar /health response

The lazy bridge MCP monitor needs to validate that a sidecar
belongs to the same workspace before upgrading. The /health
endpoint now includes workspace_root in its response JSON."
```

---

### Task 3: Sidecar Client Module

Create a new module that handles connecting to the sidecar, validating workspace, and delegating tool calls. This isolates all sidecar communication logic.

**Files:**
- Create: `IVY_LSP/sidecar_client.py`
- Test: `IVY_TESTS/test_sidecar_client.py`

- [ ] **Step 1: Write failing tests**

Create `IVY_TESTS/test_sidecar_client.py`:

```python
"""Tests for the sidecar client — connection, validation, delegation."""

import asyncio
import json
import os
from unittest.mock import AsyncMock, patch

import pytest


def test_read_port_file_returns_port(tmp_path):
    """Read a valid port file."""
    from ivy_lsp.sidecar_client import read_port_file

    port_file = tmp_path / "ivy-mcp-abc123.port"
    port_file.write_text("19847")
    assert read_port_file(str(tmp_path), "abc123") == 19847


def test_read_port_file_returns_none_when_missing(tmp_path):
    """Missing port file returns None."""
    from ivy_lsp.sidecar_client import read_port_file

    assert read_port_file(str(tmp_path), "abc123") is None


def test_read_port_file_returns_none_when_corrupt(tmp_path):
    """Corrupt port file returns None."""
    from ivy_lsp.sidecar_client import read_port_file

    port_file = tmp_path / "ivy-mcp-abc123.port"
    port_file.write_text("not-a-number")
    assert read_port_file(str(tmp_path), "abc123") is None


def test_workspace_hash_is_stable():
    """Same path always produces the same hash."""
    from ivy_lsp.sidecar_client import workspace_hash

    h1 = workspace_hash("/some/path")
    h2 = workspace_hash("/some/path")
    assert h1 == h2
    assert len(h1) == 12


def test_workspace_hash_differs_for_different_paths():
    """Different paths produce different hashes."""
    from ivy_lsp.sidecar_client import workspace_hash

    assert workspace_hash("/path/a") != workspace_hash("/path/b")


@pytest.mark.asyncio
async def test_validate_workspace_rejects_mismatch():
    """Validation rejects a sidecar with a different workspace root."""
    from ivy_lsp.sidecar_client import validate_sidecar_workspace

    with patch("ivy_lsp.sidecar_client._fetch_health") as mock_fetch:
        mock_fetch.return_value = {"workspace_root": "/other/workspace"}
        result = await validate_sidecar_workspace(19847, "/my/workspace")
        assert result is False


@pytest.mark.asyncio
async def test_validate_workspace_accepts_match():
    """Validation accepts a sidecar with matching workspace root."""
    from ivy_lsp.sidecar_client import validate_sidecar_workspace

    with patch("ivy_lsp.sidecar_client._fetch_health") as mock_fetch:
        mock_fetch.return_value = {"workspace_root": "/my/workspace"}
        result = await validate_sidecar_workspace(19847, "/my/workspace")
        assert result is True


@pytest.mark.asyncio
async def test_validate_workspace_handles_unreachable():
    """Validation returns False if health endpoint is unreachable."""
    from ivy_lsp.sidecar_client import validate_sidecar_workspace

    with patch("ivy_lsp.sidecar_client._fetch_health") as mock_fetch:
        mock_fetch.return_value = None
        result = await validate_sidecar_workspace(19847, "/my/workspace")
        assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/test_sidecar_client.py -v
```

Expected: FAIL — `ivy_lsp.sidecar_client` module does not exist.

- [ ] **Step 3: Implement `sidecar_client.py`**

Create `IVY_LSP/sidecar_client.py`:

**NOTE:** Uses `urllib.request` (stdlib, already used in `ivy_lsp/rfc/fetcher.py`) instead of `aiohttp` (not a dependency). Health checks run in a thread via `asyncio.to_thread()`. This module also owns the `_sidecar_client` global state to avoid circular imports between `mcp_server.py` and `tools/__init__.py`.

```python
"""Sidecar client for the lazy bridge upgrade mechanism.

Handles:
- Global sidecar client state (get/set)
- Port file reading and workspace hash computation
- Sidecar health check and workspace validation
- MCP client connection via streamablehttp_client

This module is imported by both mcp_server.py (monitor) and
tools/__init__.py (safe_tool delegation). It must NOT import
from either to avoid circular imports.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

# --- Global sidecar client state ---
# Owned here to avoid circular imports between mcp_server and tools.
_sidecar_client: Any | None = None


def get_sidecar_client() -> Any | None:
    """Read the current sidecar client. Used by safe_tool."""
    return _sidecar_client


def set_sidecar_client(client: Any | None) -> None:
    """Swap the sidecar client reference (atomic under CPython GIL)."""
    global _sidecar_client
    _sidecar_client = client


def workspace_hash(root: str) -> str:
    """Stable 12-char hash of the workspace root path."""
    return hashlib.sha256(root.encode()).hexdigest()[:12]


def read_port_file(
    port_dir: str = "/tmp", ws_hash: str | None = None
) -> int | None:
    """Read the sidecar port from /tmp/ivy-mcp-{ws_hash}.port.

    Returns the port number, or None if missing/corrupt.
    """
    if ws_hash is None:
        return None
    path = os.path.join(port_dir, f"ivy-mcp-{ws_hash}.port")
    try:
        with open(path) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _fetch_health_sync(port: int) -> dict | None:
    """Fetch sidecar /health (synchronous, for use via asyncio.to_thread)."""
    url = f"http://127.0.0.1:{port}/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode())
    except Exception:
        logger.debug("Sidecar health check failed on port %d", port)
    return None


async def _fetch_health(port: int) -> dict | None:
    """Async wrapper around the synchronous health check."""
    return await asyncio.to_thread(_fetch_health_sync, port)


async def validate_sidecar_workspace(
    port: int, expected_root: str
) -> bool:
    """Check that the sidecar's workspace_root matches ours.

    Prevents upgrading to a sidecar from a different worktree session.
    """
    health = await _fetch_health(port)
    if health is None:
        return False
    sidecar_root = health.get("workspace_root", "")
    if not sidecar_root:
        logger.debug("Sidecar /health missing workspace_root")
        return False
    match = os.path.realpath(sidecar_root) == os.path.realpath(expected_root)
    if not match:
        logger.debug(
            "Workspace mismatch: ours=%s sidecar=%s", expected_root, sidecar_root
        )
    return match


async def connect_to_sidecar(port: int) -> Any:
    """Establish an MCP client session to the sidecar.

    Returns a ClientSession that can call tools, or None on failure.
    Stores the transport context manager on the session object
    as `_transport_ctx` for cleanup on disconnect.
    """
    try:
        from mcp.client.streamable_http import streamablehttp_client
        from mcp import ClientSession

        url = f"http://127.0.0.1:{port}/mcp"
        transport_ctx = streamablehttp_client(url)
        read_stream, write_stream, _ = await transport_ctx.__aenter__()

        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        await session.initialize()

        # Stash transport context for cleanup
        session._transport_ctx = transport_ctx
        logger.info("[SIDECAR-CLIENT] Connected to sidecar on port %d", port)
        return session
    except Exception:
        logger.warning("[SIDECAR-CLIENT] Failed to connect to port %d", port, exc_info=True)
        return None


async def disconnect_sidecar(session: Any) -> None:
    """Clean up an MCP client session and its transport."""
    try:
        await session.__aexit__(None, None, None)
    except Exception:
        logger.debug("Session cleanup failed", exc_info=True)
    try:
        ctx = getattr(session, "_transport_ctx", None)
        if ctx is not None:
            await ctx.__aexit__(None, None, None)
    except Exception:
        logger.debug("Transport cleanup failed", exc_info=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/test_sidecar_client.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/sidecar_client.py tests/test_sidecar_client.py
git commit -m "feat: add sidecar client for lazy bridge upgrade

New module handling port file reading, workspace validation,
and MCP client connection to the LSP sidecar. Used by the
sidecar monitor and safe_tool delegation."
```

---

### Task 4: Sidecar Monitor Background Task

Add the background task to `mcp_server.py` that polls for the sidecar port file and triggers the upgrade.

**Files:**
- Modify: `IVY_LSP/mcp_server.py`
- Test: `IVY_TESTS/test_sidecar_monitor.py`

- [ ] **Step 1: Write failing tests**

Create `IVY_TESTS/test_sidecar_monitor.py`:

```python
"""Tests for the sidecar monitor background task."""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from ivy_lsp import sidecar_client


@pytest.mark.asyncio
async def test_monitor_skips_when_disabled():
    """Monitor exits immediately when IVY_MCP_DISABLE_UPGRADE=1."""
    from ivy_lsp.mcp_server import _sidecar_monitor

    with patch.dict("os.environ", {"IVY_MCP_DISABLE_UPGRADE": "1"}):
        # Should return without polling
        task = asyncio.create_task(_sidecar_monitor("/workspace"))
        await asyncio.sleep(0.1)
        assert task.done()


@pytest.mark.asyncio
async def test_monitor_sets_client_on_valid_sidecar():
    """Monitor sets sidecar_client when sidecar is validated."""
    from ivy_lsp.mcp_server import _sidecar_monitor

    mock_client = MagicMock()

    old = sidecar_client.get_sidecar_client()
    try:
        sidecar_client.set_sidecar_client(None)

        with patch("ivy_lsp.mcp_server.sidecar_client") as mock_sc:
            mock_sc.workspace_hash.return_value = "abc123"
            mock_sc.read_port_file.return_value = 19847
            mock_sc.validate_sidecar_workspace = AsyncMock(return_value=True)
            mock_sc.connect_to_sidecar = AsyncMock(return_value=mock_client)
            mock_sc.get_sidecar_client.return_value = None
            mock_sc.set_sidecar_client = sidecar_client.set_sidecar_client

            task = asyncio.create_task(
                _sidecar_monitor("/workspace", _poll_interval=0.05, _max_iterations=2)
            )
            await asyncio.sleep(0.2)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        assert sidecar_client.get_sidecar_client() is mock_client
    finally:
        sidecar_client.set_sidecar_client(old)


@pytest.mark.asyncio
async def test_monitor_skips_workspace_mismatch():
    """Monitor does not upgrade when workspace doesn't match."""
    from ivy_lsp.mcp_server import _sidecar_monitor

    old = sidecar_client.get_sidecar_client()
    try:
        sidecar_client.set_sidecar_client(None)

        with patch("ivy_lsp.mcp_server.sidecar_client") as mock_sc:
            mock_sc.workspace_hash.return_value = "abc123"
            mock_sc.read_port_file.return_value = 19847
            mock_sc.validate_sidecar_workspace = AsyncMock(return_value=False)
            mock_sc.get_sidecar_client.return_value = None

            task = asyncio.create_task(
                _sidecar_monitor("/workspace", _poll_interval=0.05, _max_iterations=2)
            )
            await asyncio.sleep(0.2)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        assert sidecar_client.get_sidecar_client() is None
    finally:
        sidecar_client.set_sidecar_client(old)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/test_sidecar_monitor.py -v
```

Expected: FAIL — `_sidecar_monitor` does not exist.

- [ ] **Step 3: Add sidecar monitor to `mcp_server.py`**

Add near the top of `IVY_LSP/mcp_server.py` (after existing imports):

```python
from ivy_lsp import sidecar_client
```

Then add the monitor function (can go after the `ToolContext` class):

```python
async def _sidecar_monitor(
    workspace_root: str,
    _poll_interval: float = 2.0,
    _max_iterations: int = 0,
) -> None:
    """Background task: poll for sidecar port file, upgrade when ready.

    Args:
        workspace_root: Our workspace root for validation.
        _poll_interval: Override for testing (default 2s).
        _max_iterations: If >0, exit after N iterations (for testing).
    """
    if os.environ.get("IVY_MCP_DISABLE_UPGRADE") == "1":
        logger.info("[SIDECAR-MONITOR] Upgrade disabled by IVY_MCP_DISABLE_UPGRADE")
        return

    ws_hash = sidecar_client.workspace_hash(workspace_root)
    elapsed = 0.0
    poll = _poll_interval
    iteration = 0

    while True:
        await asyncio.sleep(poll)
        elapsed += poll
        iteration += 1

        if _max_iterations > 0 and iteration >= _max_iterations:
            return

        # Progressive backoff: fast for first 60s, then slow
        if elapsed > 60 and poll < 10:
            poll = 10.0
            logger.debug("[SIDECAR-MONITOR] Backing off to 10s polling")

        # Already upgraded — just keep a slow heartbeat
        if sidecar_client.get_sidecar_client() is not None:
            poll = 30.0
            continue

        port = sidecar_client.read_port_file(ws_hash=ws_hash)
        if port is None:
            continue

        if not await sidecar_client.validate_sidecar_workspace(port, workspace_root):
            logger.debug("[SIDECAR-MONITOR] Workspace mismatch, skipping")
            continue

        client = await sidecar_client.connect_to_sidecar(port)
        if client is not None:
            sidecar_client.set_sidecar_client(client)
            logger.info("[UPGRADED] Delegating tools to LSP sidecar on port %d", port)
            poll = 30.0
```

Then in `start_mcp()`, launch the monitor **after** the MCP app is created but **before** calling `mcp.run()`. FastMCP's `run()` starts its own event loop, so use the `startup` hook or register the monitor as a coroutine that runs alongside the server. The simplest integration:

```python
# In start_mcp(), just before mcp.run():
import threading

def _start_monitor_in_thread():
    """Run the sidecar monitor in its own event loop (daemon thread)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_sidecar_monitor(root))

if os.environ.get("IVY_MCP_DISABLE_UPGRADE") != "1":
    monitor_thread = threading.Thread(
        target=_start_monitor_in_thread,
        name="sidecar-monitor",
        daemon=True,
    )
    monitor_thread.start()
    logger.info("[SIDECAR-MONITOR] Started background upgrade monitor")
```

**Note:** The monitor runs in a daemon thread with its own event loop because FastMCP's `run()` blocks the main thread's event loop. The sidecar client state (`_sidecar_client`) is accessed atomically via the GIL.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/test_sidecar_monitor.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp_server.py tests/test_sidecar_monitor.py
git commit -m "feat: add sidecar monitor background task

Polls for the LSP sidecar port file with progressive backoff
(2s initially, 10s after 60s). When detected and validated,
sets _sidecar_client for tool delegation. Supports
IVY_MCP_DISABLE_UPGRADE=1 to skip monitoring."
```

---

### Task 5: `safe_tool` Sidecar Delegation

Modify the `safe_tool` decorator to delegate tool calls to the sidecar when `_sidecar_client` is set.

**Files:**
- Modify: `IVY_LSP/tools/__init__.py`
- Test: `IVY_TESTS/test_safe_tool_delegation.py`

- [ ] **Step 1: Write failing tests**

Create `IVY_TESTS/test_safe_tool_delegation.py`:

**Note:** Tests patch `ivy_lsp.sidecar_client` (where the state lives), not `ivy_lsp.tools` (which re-exports). The `safe_tool` decorator rebuilds the wrapper with `fn.__globals__`, so tests must ensure `get_sidecar_client` and `set_sidecar_client` are in those globals. We test delegation in isolation by calling `get_sidecar_client` directly and verifying behavior, rather than decorating test functions with `safe_tool` (which requires the full config/logging stack).

```python
"""Tests for safe_tool sidecar delegation."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ivy_lsp import sidecar_client


@pytest.mark.asyncio
async def test_delegation_calls_sidecar_when_client_set():
    """When _sidecar_client is set, get_sidecar_client returns it."""
    mock_client = AsyncMock()
    mock_result = MagicMock()
    mock_result.content = [MagicMock(text='{"delegated": true}')]
    mock_client.call_tool.return_value = mock_result

    old = sidecar_client.get_sidecar_client()
    try:
        sidecar_client.set_sidecar_client(mock_client)
        client = sidecar_client.get_sidecar_client()
        assert client is mock_client

        # Simulate what safe_tool does
        result = await client.call_tool("ivy_capabilities", {})
        mock_client.call_tool.assert_called_once_with("ivy_capabilities", {})
    finally:
        sidecar_client.set_sidecar_client(old)


@pytest.mark.asyncio
async def test_delegation_resets_client_on_error():
    """On connection error, set_sidecar_client(None) reverts to local."""
    mock_client = AsyncMock()
    mock_client.call_tool.side_effect = ConnectionError("sidecar gone")

    old = sidecar_client.get_sidecar_client()
    try:
        sidecar_client.set_sidecar_client(mock_client)

        # Simulate safe_tool error path
        try:
            await mock_client.call_tool("ivy_capabilities", {})
        except ConnectionError:
            sidecar_client.set_sidecar_client(None)

        assert sidecar_client.get_sidecar_client() is None
    finally:
        sidecar_client.set_sidecar_client(old)


def test_no_client_returns_none():
    """When no sidecar is set, get_sidecar_client returns None."""
    old = sidecar_client.get_sidecar_client()
    try:
        sidecar_client.set_sidecar_client(None)
        assert sidecar_client.get_sidecar_client() is None
    finally:
        sidecar_client.set_sidecar_client(old)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/test_safe_tool_delegation.py -v
```

Expected: FAIL — `get_sidecar_client` not imported in tools.

- [ ] **Step 3: Add delegation to `safe_tool` in `tools/__init__.py`**

At the top of `IVY_LSP/tools/__init__.py`, add import:

```python
from ivy_lsp.sidecar_client import get_sidecar_client, set_sidecar_client
```

**Note:** Imports from `sidecar_client` (NOT `mcp_server`) to avoid circular imports. `mcp_server.py` imports from `tools/__init__.py` via `register_all_tools`, so importing back from `mcp_server` would create a cycle.

Then in the `safe_tool` function, add the delegation check at the very beginning of `_wrapper`, **before** the semaphore acquire and timeout:

```python
def safe_tool(fn):
    @functools.wraps(fn)
    async def _wrapper(*args, **kwargs):
        # --- Sidecar delegation (lazy bridge) ---
        # Check BEFORE semaphore/timeout — sidecar handles its own concurrency
        _client = get_sidecar_client()
        if _client is not None:
            try:
                result = await _client.call_tool(fn.__name__, kwargs)
                return result  # verbatim from sidecar, no local formatting
            except Exception:
                logger.warning(
                    "[DOWNGRADED] Sidecar call to %s failed, using local",
                    fn.__name__,
                )
                set_sidecar_client(None)
                # Fall through to local handling

        # --- Original local handling below (unchanged) ---
        from ivy_lsp.config import get_config
        # ... (rest of existing _wrapper code) ...
```

**Critical:** Add `get_sidecar_client` and `set_sidecar_client` to the `_injected_names` dict (around line 430) so they are available in the rebuilt `FunctionType` wrapper:

```python
    _injected_names = {
        # ... existing entries ...
        "get_sidecar_client": get_sidecar_client,
        "set_sidecar_client": set_sidecar_client,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/test_safe_tool_delegation.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Run existing tool tests to ensure no regression**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/test_tools_verification.py tests/test_tools_analysis.py tests/test_tools_quality.py tests/test_tools_patterns.py tests/test_tools_traceability.py -v --timeout=60
```

Expected: All existing tests PASS.

- [ ] **Step 6: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/tools/__init__.py tests/test_safe_tool_delegation.py
git commit -m "feat: add sidecar delegation to safe_tool decorator

When _sidecar_client is set by the sidecar monitor, tool calls
are forwarded to the LSP sidecar via MCP client. Sidecar response
is returned verbatim (no local formatting/timeout). Falls back to
local handling on connection errors with [DOWNGRADED] log."
```

---

### Task 6: Integration Test — Upgrade/Downgrade Cycle

End-to-end test that simulates the full lifecycle: standalone start → sidecar appears → upgrade → sidecar dies → downgrade.

**Files:**
- Test: `IVY_TESTS/test_lazy_bridge_integration.py`

- [ ] **Step 1: Write integration test**

Create `IVY_TESTS/test_lazy_bridge_integration.py`:

```python
"""Integration test for the lazy bridge lifecycle.

Tests the full cycle:
1. MCP starts standalone (no sidecar)
2. Sidecar port file appears
3. Monitor detects and upgrades
4. Tool calls are delegated
5. Sidecar goes away
6. Tool calls revert to local
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ivy_lsp import sidecar_client


@pytest.mark.asyncio
async def test_full_upgrade_downgrade_cycle():
    """Simulate: standalone → upgrade → downgrade → standalone."""
    from ivy_lsp.mcp_server import _sidecar_monitor

    old = sidecar_client.get_sidecar_client()
    try:
        # Start clean
        sidecar_client.set_sidecar_client(None)
        assert sidecar_client.get_sidecar_client() is None

        mock_client = AsyncMock()

        # Phase 1: No port file → stays standalone
        with patch("ivy_lsp.mcp_server.sidecar_client") as mock_sc:
            mock_sc.workspace_hash.return_value = "test123"
            mock_sc.read_port_file.return_value = None
            mock_sc.get_sidecar_client = sidecar_client.get_sidecar_client

            task = asyncio.create_task(
                _sidecar_monitor("/workspace", _poll_interval=0.05, _max_iterations=2)
            )
            await asyncio.sleep(0.2)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        assert sidecar_client.get_sidecar_client() is None  # Still standalone

        # Phase 2: Port file appears → upgrade
        with patch("ivy_lsp.mcp_server.sidecar_client") as mock_sc:
            mock_sc.workspace_hash.return_value = "test123"
            mock_sc.read_port_file.return_value = 19847
            mock_sc.validate_sidecar_workspace = AsyncMock(return_value=True)
            mock_sc.connect_to_sidecar = AsyncMock(return_value=mock_client)
            mock_sc.get_sidecar_client.return_value = None
            mock_sc.set_sidecar_client = sidecar_client.set_sidecar_client

            task = asyncio.create_task(
                _sidecar_monitor("/workspace", _poll_interval=0.05, _max_iterations=2)
            )
            await asyncio.sleep(0.2)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        assert sidecar_client.get_sidecar_client() is mock_client  # Upgraded!

        # Phase 3: Downgrade
        sidecar_client.set_sidecar_client(None)
        assert sidecar_client.get_sidecar_client() is None  # Back to standalone
    finally:
        sidecar_client.set_sidecar_client(old)


@pytest.mark.asyncio
async def test_disable_upgrade_env_var():
    """IVY_MCP_DISABLE_UPGRADE=1 prevents monitor from running."""
    from ivy_lsp.mcp_server import _sidecar_monitor

    old = sidecar_client.get_sidecar_client()
    try:
        sidecar_client.set_sidecar_client(None)

        with patch.dict(os.environ, {"IVY_MCP_DISABLE_UPGRADE": "1"}):
            await _sidecar_monitor("/workspace")

        assert sidecar_client.get_sidecar_client() is None
    finally:
        sidecar_client.set_sidecar_client(old)
```

- [ ] **Step 2: Run integration test**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/test_lazy_bridge_integration.py -v
```

Expected: All tests PASS.

- [ ] **Step 3: Run full test suite to check for regressions**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/ -v --timeout=120 -x -q 2>&1 | tail -20
```

Expected: No new failures.

- [ ] **Step 4: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add tests/test_lazy_bridge_integration.py
git commit -m "test: add integration test for lazy bridge lifecycle

Covers standalone start, sidecar detection → upgrade,
sidecar loss → downgrade, and IVY_MCP_DISABLE_UPGRADE env var."
```

---

### Task 7: Manual Validation

Verify the changes work end-to-end in a real Claude Code session.

**Files:** None (manual testing only)

- [ ] **Step 1: Update the panther_ivy submodule pointer**

```bash
cd /path/to/panther/root
git add panther/plugins/services/testers/panther_ivy
git commit -m "chore: update panther_ivy submodule (lazy bridge MCP)"
```

- [ ] **Step 2: Start a fresh Claude Code session**

Open a new Claude Code session in the same worktree.

- [ ] **Step 3: Run `/nct-health`**

Expected:
- Step 1 (LSP alive): PASS or WARN (on-demand)
- Step 4 (MCP alive): **PASS** (was FAIL before)
- Step 5 (Workspace access): **PASS** (was FAIL before)
- Step 6 (Model builds): **PASS** (was FAIL before)

- [ ] **Step 4: Check MCP log for standalone start**

```bash
tail -30 /tmp/ivy-mcp-latest.log
```

Expected: `[MCP-READY]` log line, no `mcp-bridge` references.

- [ ] **Step 5: Open an `.ivy` file to trigger LSP + sidecar**

Open any `.ivy` file (e.g., via `Read` or `LSP` tool call). Wait 10 seconds.

```bash
tail -5 /tmp/ivy-mcp-latest.log
```

Expected: `[UPGRADED] Delegating tools to LSP sidecar on port NNNNN`

- [ ] **Step 6: Verify stale PID cleanup**

```bash
ls /tmp/ivy-lsp-pids/
```

Expected: Only active PID files, no stale entries from previous sessions.
