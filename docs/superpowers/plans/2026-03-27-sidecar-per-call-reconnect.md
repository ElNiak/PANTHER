# Sidecar Per-Call Reconnect Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the MCP sidecar SSE connection cleanup race that freezes the event loop by replacing the cached-client pattern with per-call connections using proper `async with` scoping.

**Architecture:** Each tool call creates a fresh `streamablehttp_client` + `ClientSession` within nested `async with` blocks, calls the tool, and lets the context managers handle cleanup. The global `_sidecar_client` cache is removed from the hot path. Port discovery (monitor thread) is unchanged.

**Tech Stack:** Python 3.10+, MCP SDK (`mcp.client.streamable_http`), asyncio, anyio

**Base directory for all relative paths:** `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`

---

### Task 1: Move `_cancel_safe_wait_for` to `client.py`

**Files:**
- Modify: `ivy_lsp/mcp/client.py`
- Modify: `ivy_lsp/mcp/tools/__init__.py:262-279`
- Test: `tests/test_safe_tool_delegation.py`

- [ ] **Step 1: Add `_cancel_safe_wait_for` to `client.py`**

Add at the bottom of `ivy_lsp/mcp/client.py`, after `disconnect_sidecar`:

```python
async def _cancel_safe_wait_for(coro, timeout):
    """Like ``asyncio.wait_for`` but prevents ``CancelledError`` from leaking.

    Uses ``asyncio.wait()`` + manual cancel instead of ``wait_for()``, so the
    cancellation happens on a child task — not on the transport-bound calling
    task.  This prevents ``CancelledError`` from disrupting the HTTP/SSE
    connection that delivers the timeout response to the client.
    """
    task = asyncio.ensure_future(coro)
    done, _ = await asyncio.wait({task}, timeout=timeout)
    if task in done:
        return task.result()
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass
    raise asyncio.TimeoutError()
```

- [ ] **Step 2: Update `tools/__init__.py` to import from `client.py`**

In `ivy_lsp/mcp/tools/__init__.py`, replace the local `_cancel_safe_wait_for` definition (lines 262-279) with:

```python
from ivy_lsp.mcp.client import _cancel_safe_wait_for  # moved here to avoid circular import
```

Keep the old docstring as a comment if desired, but remove the function body.

- [ ] **Step 3: Run existing tests to verify no regression**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_safe_tool_delegation.py -v`

Expected: All 10 tests pass. The import path changed but `_cancel_safe_wait_for` is re-exported from `tools/__init__` via the import, so existing test imports (`from ivy_lsp.mcp.tools import _cancel_safe_wait_for`) still work.

- [ ] **Step 4: Commit**

```bash
git add ivy_lsp/mcp/client.py ivy_lsp/mcp/tools/__init__.py
git commit -m "refactor: move _cancel_safe_wait_for to client.py to avoid circular import"
```

---

### Task 2: Add `call_sidecar_once` to `client.py`

**Files:**
- Modify: `ivy_lsp/mcp/client.py`
- Test: `tests/test_safe_tool_delegation.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_safe_tool_delegation.py`:

```python
@pytest.mark.asyncio
async def test_call_sidecar_once_success():
    """call_sidecar_once returns result on success and cleans up."""
    from ivy_lsp.mcp.client import call_sidecar_once

    mock_result = MagicMock()
    mock_result.content = [MagicMock(text='{"ok": true}')]

    mock_session_cls = AsyncMock()
    mock_session_instance = AsyncMock()
    mock_session_instance.initialize = AsyncMock()
    mock_session_instance.list_tools = AsyncMock(return_value=MagicMock(tools=[]))
    mock_session_instance.call_tool = AsyncMock(return_value=mock_result)
    mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_session_instance.__aexit__ = AsyncMock(return_value=False)
    mock_session_cls.return_value = mock_session_instance

    mock_transport = AsyncMock()
    mock_read, mock_write = AsyncMock(), AsyncMock()
    mock_transport.__aenter__ = AsyncMock(return_value=(mock_read, mock_write, None))
    mock_transport.__aexit__ = AsyncMock(return_value=False)

    with patch("ivy_lsp.mcp.client.streamablehttp_client", return_value=mock_transport):
        with patch("ivy_lsp.mcp.client.ClientSession", mock_session_cls):
            result = await call_sidecar_once(19847, "ivy_capabilities", {}, 5.0)

    assert result is mock_result
    mock_session_instance.call_tool.assert_called_once_with("ivy_capabilities", {})


@pytest.mark.asyncio
async def test_call_sidecar_once_connection_failure_returns_none():
    """call_sidecar_once returns None when connection fails."""
    from ivy_lsp.mcp.client import call_sidecar_once

    with patch(
        "ivy_lsp.mcp.client.streamablehttp_client",
        side_effect=ConnectionError("refused"),
    ):
        result = await call_sidecar_once(19847, "ivy_test", {}, 5.0)

    assert result is None


@pytest.mark.asyncio
async def test_call_sidecar_once_timeout_returns_none():
    """call_sidecar_once returns None when tool call times out."""
    from ivy_lsp.mcp.client import call_sidecar_once

    mock_session_instance = AsyncMock()
    mock_session_instance.initialize = AsyncMock()
    mock_session_instance.list_tools = AsyncMock(return_value=MagicMock(tools=[]))
    mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_session_instance.__aexit__ = AsyncMock(return_value=False)

    async def hang(*args, **kwargs):
        await asyncio.sleep(999)

    mock_session_instance.call_tool.side_effect = hang

    mock_transport = AsyncMock()
    mock_read, mock_write = AsyncMock(), AsyncMock()
    mock_transport.__aenter__ = AsyncMock(return_value=(mock_read, mock_write, None))
    mock_transport.__aexit__ = AsyncMock(return_value=False)

    with patch("ivy_lsp.mcp.client.streamablehttp_client", return_value=mock_transport):
        with patch("ivy_lsp.mcp.client.ClientSession", return_value=mock_session_instance):
            result = await call_sidecar_once(19847, "ivy_test", {}, 0.05)

    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_safe_tool_delegation.py::test_call_sidecar_once_success tests/test_safe_tool_delegation.py::test_call_sidecar_once_connection_failure_returns_none tests/test_safe_tool_delegation.py::test_call_sidecar_once_timeout_returns_none -v`

Expected: FAIL with `ImportError: cannot import name 'call_sidecar_once'`

- [ ] **Step 3: Implement `call_sidecar_once` in `client.py`**

Add to `ivy_lsp/mcp/client.py` after the existing imports, add new imports:

```python
from typing import Any
```

is already there. Add at the top-level, after the existing `_sidecar_port` global:

```python
_list_tools_cache: dict[int, bool] = {}
```

Add the function after `disconnect_sidecar`:

```python
async def call_sidecar_once(
    port: int, tool_name: str, kwargs: dict, timeout: float
) -> Any:
    """Single-shot sidecar call with per-call connection lifecycle.

    Creates a fresh streamablehttp_client + ClientSession, calls the tool,
    and lets async-with scoping handle all cleanup. Returns the CallToolResult
    on success, or None on any failure (caller falls through to local).
    """
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    url = f"http://127.0.0.1:{port}/mcp"
    try:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Pre-cache tool schemas to prevent MCP SDK deadlock:
                # call_tool() may trigger _validate_tool_result() which calls
                # list_tools() on the same connection — deadlock on SSE transport.
                if port not in _list_tools_cache:
                    await session.list_tools()
                    _list_tools_cache[port] = True
                return await _cancel_safe_wait_for(
                    session.call_tool(tool_name, kwargs), timeout
                )
    except asyncio.TimeoutError:
        logger.warning(
            "[SIDECAR-TIMEOUT] %s timed out after %.1fs", tool_name, timeout
        )
        return None
    except Exception:
        logger.warning(
            "[SIDECAR-ERROR] %s call failed", tool_name, exc_info=True
        )
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_safe_tool_delegation.py -v`

Expected: All tests pass (old + 3 new).

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/mcp/client.py tests/test_safe_tool_delegation.py
git commit -m "feat: add call_sidecar_once with per-call connection lifecycle"
```

---

### Task 3: Rewire `safe_tool` to use `call_sidecar_once`

**Files:**
- Modify: `ivy_lsp/mcp/tools/__init__.py:373-441` (sidecar delegation block)
- Modify: `ivy_lsp/mcp/tools/__init__.py:686-710` (`_injected_names`)

- [ ] **Step 1: Replace the sidecar delegation block in `safe_tool`**

In `ivy_lsp/mcp/tools/__init__.py`, replace lines 373-441 (the entire sidecar delegation section inside `_wrapper`) with:

```python
            # --- Sidecar delegation (per-call connection) ---
            # Each call creates a fresh transport + session to avoid SSE
            # cleanup race conditions in the MCP SDK's streamablehttp_client.
            from ivy_lsp.mcp.client import call_sidecar_once, get_sidecar_port
            from ivy_lsp.infra.config import get_config as _get_cfg

            _port = get_sidecar_port()
            if _port is not None:
                _sidecar_timeout = _get_cfg().sidecar_delegation_timeout
                logger.debug(
                    "[TOOL-ROUTE] %s -> sidecar (port %s, timeout=%.1fs)",
                    tool_name,
                    _port,
                    _sidecar_timeout,
                )
                _sidecar_result = await call_sidecar_once(
                    _port, tool_name, kwargs, _sidecar_timeout
                )
                if _sidecar_result is not None:
                    return _sidecar_result
                logger.debug(
                    "[TOOL-ROUTE] %s -> local (sidecar fallback)", tool_name
                )
            else:
                logger.debug("[TOOL-ROUTE] %s -> local (no sidecar)", tool_name)
```

- [ ] **Step 2: Update `_injected_names`**

In the `_injected_names` dict (around line 686), replace the three cached-client entries:

```python
            "get_sidecar_client": get_sidecar_client,
            "set_sidecar_client": set_sidecar_client,
            "_cleanup_sidecar": _cleanup_sidecar,
```

with:

```python
            "call_sidecar_once": call_sidecar_once,
```

And add the import at the top of the file (near line 212):

```python
from ivy_lsp.mcp.client import get_sidecar_client, set_sidecar_client, call_sidecar_once
```

(Keep `get_sidecar_client` and `set_sidecar_client` imports — they're still used by `_cleanup_sidecar` and may be referenced elsewhere.)

- [ ] **Step 3: Run tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_safe_tool_delegation.py tests/test_safe_tool_semaphore.py -v`

Expected: All pass. The `_cancel_safe_wait_for` tests still pass (imported via `client.py`). The cached-client delegation tests (test_delegation_calls_sidecar_when_client_set, test_sidecar_timeout_disconnects_client, etc.) still pass because they test the `client.py` module directly, not the `safe_tool` wrapper.

- [ ] **Step 4: Commit**

```bash
git add ivy_lsp/mcp/tools/__init__.py
git commit -m "feat: rewire safe_tool to use per-call sidecar connections"
```

---

### Task 4: Fix `_sidecar_monitor` heartbeat check

**Files:**
- Modify: `ivy_lsp/mcp/server.py:102-105`
- Test: `tests/test_sidecar_monitor.py`

- [ ] **Step 1: Write a failing test for the new heartbeat check**

Add to `tests/test_sidecar_monitor.py`:

```python
@pytest.mark.asyncio
async def test_monitor_backs_off_when_port_known():
    """Monitor backs off to 30s polling when sidecar port is already set."""
    from ivy_lsp.mcp.server import _sidecar_monitor

    old_port = sidecar_client.get_sidecar_port()
    old_client = sidecar_client.get_sidecar_client()
    try:
        # Port is known but no cached client (per-call pattern)
        sidecar_client.set_sidecar_port(19847)
        sidecar_client.set_sidecar_client(None)

        with patch("ivy_lsp.mcp.server.sidecar_client") as mock_sc:
            mock_sc.workspace_hash.return_value = "abc123"
            mock_sc.get_sidecar_port.return_value = 19847
            # get_sidecar_client is None — this is the new per-call world
            mock_sc.get_sidecar_client.return_value = None

            task = asyncio.create_task(
                _sidecar_monitor("/workspace", _poll_interval=0.05, _max_iterations=3)
            )
            await asyncio.sleep(0.3)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Monitor should NOT have tried read_port_file or validate_sidecar_workspace
        # because it backed off immediately when port was already known
        mock_sc.read_port_file.assert_not_called()
    finally:
        sidecar_client.set_sidecar_port(old_port)
        sidecar_client.set_sidecar_client(old_client)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_sidecar_monitor.py::test_monitor_backs_off_when_port_known -v`

Expected: FAIL — the current code checks `get_sidecar_client()` which returns `None`, so it doesn't back off and still calls `read_port_file`.

- [ ] **Step 3: Fix the heartbeat check in `server.py`**

In `ivy_lsp/mcp/server.py`, replace lines 102-105:

```python
        # Already upgraded — just keep a slow heartbeat
        if sidecar_client.get_sidecar_client() is not None:
            poll = 30.0
            continue
```

with:

```python
        # Already discovered — just keep a slow heartbeat.
        # Check port (not client) because per-call pattern doesn't cache clients.
        if sidecar_client.get_sidecar_port() is not None:
            poll = 30.0
            continue
```

- [ ] **Step 4: Run all monitor tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_sidecar_monitor.py -v`

Expected: All 4 tests pass (3 existing + 1 new).

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/mcp/server.py tests/test_sidecar_monitor.py
git commit -m "fix: monitor heartbeat checks port instead of cached client"
```

---

### Task 5: Update existing delegation tests

**Files:**
- Modify: `tests/test_safe_tool_delegation.py`

The existing tests for cached-client delegation (`test_delegation_calls_sidecar_when_client_set`, `test_delegation_resets_client_on_error`, `test_sidecar_timeout_disconnects_client`, `test_sidecar_connection_error_still_downgrades`) test the old pattern by manipulating global state. These tests still pass because they test `client.py` module functions directly, not the `safe_tool` wrapper. They remain valid as unit tests of the `get/set_sidecar_client` API.

However, we should add integration-style tests that verify the new `safe_tool` behavior.

- [ ] **Step 1: Add integration test for sidecar-to-local fallback**

Add to `tests/test_safe_tool_delegation.py`:

```python
@pytest.mark.asyncio
async def test_call_sidecar_once_cleans_up_on_success():
    """Verify async-with scoping — transport.__aexit__ is called on success."""
    from ivy_lsp.mcp.client import call_sidecar_once

    mock_result = MagicMock()
    mock_result.content = [MagicMock(text='{"ok": true}')]

    mock_session_instance = AsyncMock()
    mock_session_instance.initialize = AsyncMock()
    mock_session_instance.list_tools = AsyncMock(return_value=MagicMock(tools=[]))
    mock_session_instance.call_tool = AsyncMock(return_value=mock_result)
    mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_session_instance.__aexit__ = AsyncMock(return_value=False)

    mock_transport = AsyncMock()
    mock_read, mock_write = AsyncMock(), AsyncMock()
    mock_transport.__aenter__ = AsyncMock(return_value=(mock_read, mock_write, None))
    mock_transport.__aexit__ = AsyncMock(return_value=False)

    with patch("ivy_lsp.mcp.client.streamablehttp_client", return_value=mock_transport):
        with patch("ivy_lsp.mcp.client.ClientSession", return_value=mock_session_instance):
            await call_sidecar_once(19847, "ivy_test", {}, 5.0)

    # Both context managers must have been exited
    mock_transport.__aexit__.assert_called_once()
    mock_session_instance.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_call_sidecar_once_cleans_up_on_error():
    """Verify async-with scoping — transport.__aexit__ is called even on error."""
    from ivy_lsp.mcp.client import call_sidecar_once

    mock_session_instance = AsyncMock()
    mock_session_instance.initialize = AsyncMock()
    mock_session_instance.list_tools = AsyncMock(return_value=MagicMock(tools=[]))
    mock_session_instance.call_tool = AsyncMock(side_effect=RuntimeError("boom"))
    mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_session_instance.__aexit__ = AsyncMock(return_value=False)

    mock_transport = AsyncMock()
    mock_read, mock_write = AsyncMock(), AsyncMock()
    mock_transport.__aenter__ = AsyncMock(return_value=(mock_read, mock_write, None))
    mock_transport.__aexit__ = AsyncMock(return_value=False)

    with patch("ivy_lsp.mcp.client.streamablehttp_client", return_value=mock_transport):
        with patch("ivy_lsp.mcp.client.ClientSession", return_value=mock_session_instance):
            result = await call_sidecar_once(19847, "ivy_test", {}, 5.0)

    assert result is None
    mock_transport.__aexit__.assert_called_once()
    mock_session_instance.__aexit__.assert_called_once()
```

- [ ] **Step 2: Add test for `list_tools` caching**

```python
@pytest.mark.asyncio
async def test_call_sidecar_once_caches_list_tools():
    """list_tools() is only called once per port, cached on subsequent calls."""
    from ivy_lsp.mcp import client as client_mod
    from ivy_lsp.mcp.client import call_sidecar_once

    # Clear the cache for this test
    client_mod._list_tools_cache.pop(29999, None)

    mock_result = MagicMock()
    mock_result.content = [MagicMock(text='{"ok": true}')]

    def make_session():
        s = AsyncMock()
        s.initialize = AsyncMock()
        s.list_tools = AsyncMock(return_value=MagicMock(tools=[]))
        s.call_tool = AsyncMock(return_value=mock_result)
        s.__aenter__ = AsyncMock(return_value=s)
        s.__aexit__ = AsyncMock(return_value=False)
        return s

    def make_transport():
        t = AsyncMock()
        r, w = AsyncMock(), AsyncMock()
        t.__aenter__ = AsyncMock(return_value=(r, w, None))
        t.__aexit__ = AsyncMock(return_value=False)
        return t

    sessions = [make_session(), make_session()]
    transports = [make_transport(), make_transport()]
    call_count = 0

    def session_factory(*args, **kwargs):
        nonlocal call_count
        s = sessions[call_count]
        call_count += 1
        return s

    with patch("ivy_lsp.mcp.client.streamablehttp_client", side_effect=transports):
        with patch("ivy_lsp.mcp.client.ClientSession", side_effect=session_factory):
            await call_sidecar_once(29999, "tool_a", {}, 5.0)
            await call_sidecar_once(29999, "tool_b", {}, 5.0)

    # First call: list_tools called. Second call: cached, not called.
    sessions[0].list_tools.assert_called_once()
    sessions[1].list_tools.assert_not_called()

    # Clean up
    client_mod._list_tools_cache.pop(29999, None)
```

- [ ] **Step 3: Run all tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_safe_tool_delegation.py tests/test_sidecar_monitor.py tests/test_sidecar_client.py tests/test_safe_tool_semaphore.py -v`

Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_safe_tool_delegation.py
git commit -m "test: add per-call sidecar delegation and cleanup tests"
```

---

### Task 6: Run full test suite and clean up

**Files:**
- Possibly modify: `ivy_lsp/mcp/tools/__init__.py` (remove dead imports if clean)

- [ ] **Step 1: Run the full ivy-lsp test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -v --timeout=60 2>&1 | tail -40`

Expected: No new failures introduced. Note any pre-existing failures and ignore them.

- [ ] **Step 2: Verify the sidecar delegation logging**

Check that the `[TOOL-ROUTE]` log lines still appear correctly by grep'ing the test output or reading the code:

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_safe_tool_delegation.py tests/test_sidecar_monitor.py -v --log-cli-level=DEBUG 2>&1 | grep -E 'TOOL-ROUTE|SIDECAR'
```

Expected: `[TOOL-ROUTE]` and `[SIDECAR-*]` log messages appear in test output.

- [ ] **Step 3: Remove unused imports from `tools/__init__.py` if appropriate**

If `connect_to_sidecar` is no longer imported anywhere in `tools/__init__.py`, remove it from the imports. Keep `get_sidecar_client`, `set_sidecar_client` if they're still referenced by `_cleanup_sidecar` (which is kept for `__main__.py` restart path).

- [ ] **Step 4: Final commit**

```bash
git add -u
git commit -m "chore: clean up unused imports after sidecar per-call refactor"
```
