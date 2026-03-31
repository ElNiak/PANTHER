# Sidecar Per-Call Reconnect

**Date**: 2026-03-27
**Status**: Approved (revised after review)
**Problem**: MCP sidecar SSE connection cleanup race condition freezes event loop

## Problem

The MCP `ivy-tools` server delegates tool calls to an LSP sidecar via HTTP
(`streamablehttp_client`). The current implementation caches a single
`ClientSession` globally and reuses it across tool calls. After a successful
call, the SSE stream cleanup triggers `CancelledError` and `GeneratorExit` in
the MCP SDK's `anyio.TaskGroup`, which freezes the event loop. Claude Code
never receives the response despite the server logging "Response sent".

Evidence: `ivy_capabilities` (routed locally before sidecar connects) works.
`ivy_diagnostics` (routed to sidecar after lazy connect) hangs for 236s
despite the sidecar responding in 17ms.

Root cause: long-lived SSE connections accumulate cleanup failures in the MCP
SDK's `streamablehttp_client` async generator lifecycle.

## Solution

Replace the cached-client sidecar delegation with per-call connections using
proper `async with` scoping. Each tool call creates a fresh transport +
session within nested context managers, calls the tool, and lets the context
managers handle all cleanup. No manual `__aenter__`/`__aexit__` or background
cleanup tasks needed.

## Changes

### 1. `ivy_lsp/mcp/client.py` — add `call_sidecar_once` + move `_cancel_safe_wait_for`

**Move `_cancel_safe_wait_for` from `tools/__init__.py` to `client.py`** to
avoid a circular import (`tools/__init__.py` already imports from `client.py`).
The function is a pure async utility with zero dependencies on `tools/`.

**Add `call_sidecar_once(port, tool_name, kwargs, timeout)`:**

```python
async def call_sidecar_once(port, tool_name, kwargs, timeout):
    """Single-shot sidecar call with per-call connection lifecycle.

    Creates a fresh streamablehttp_client + ClientSession, calls the tool,
    and lets async-with scoping handle all cleanup. Returns the CallToolResult
    on success, or None on any failure (caller falls through to local).
    """
    url = f"http://127.0.0.1:{port}/mcp"
    try:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Pre-cache tool schemas to prevent MCP SDK deadlock:
                # without this, call_tool() triggers _validate_tool_result()
                # which calls list_tools() on the same connection.
                _cached = _list_tools_cache.get(port)
                if _cached is None:
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

**Module-level cache for `list_tools()` results:**

```python
_list_tools_cache: dict[int, bool] = {}
```

Keyed by port. Only fetched once per sidecar instance. Saves ~10-20ms on
subsequent calls. Cleared when port changes (monitor sets a new port).

### 2. `ivy_lsp/mcp/tools/__init__.py` — simplify sidecar delegation

Replace the cached-client delegation block in `safe_tool` (lines 373-441):

Before (25 lines of cached-client logic):
```python
_client = get_sidecar_client()
if _client is None:
    _port = get_sidecar_port()
    if _port is not None:
        _client = await connect_to_sidecar(_port)
        if _client is not None:
            set_sidecar_client(_client)
if _client is not None:
    try:
        result = await _cancel_safe_wait_for(...)
        return result
    except asyncio.TimeoutError:
        _stale = _client
        set_sidecar_client(None)
        asyncio.ensure_future(_cleanup_sidecar(_stale))
    except Exception:
        set_sidecar_client(None)
        asyncio.ensure_future(_cleanup_sidecar(_stale))
```

After (7 lines):
```python
from ivy_lsp.mcp.client import call_sidecar_once, get_sidecar_port

_port = get_sidecar_port()
if _port is not None:
    _sidecar_timeout = _get_cfg().sidecar_delegation_timeout
    logger.debug("[TOOL-ROUTE] %s -> sidecar (port %s)", tool_name, _port)
    result = await call_sidecar_once(_port, tool_name, kwargs, _sidecar_timeout)
    if result is not None:
        return result
    logger.debug("[TOOL-ROUTE] %s -> local (sidecar fallback)", tool_name)
else:
    logger.debug("[TOOL-ROUTE] %s -> local (no sidecar)", tool_name)
```

**Update `_injected_names`** (line ~700) to include `call_sidecar_once` so the
`FunctionType` rebuild can resolve it.

**Update `_cancel_safe_wait_for` reference**: change from local definition to
import from `client.py`. Keep a re-export or alias if needed by other callers
in `tools/`.

### 3. `ivy_lsp/mcp/server.py` — fix monitor heartbeat

The `_sidecar_monitor` at line 103 checks `get_sidecar_client() is not None`
to back off polling. With no cached client, this always returns `None`,
causing the monitor to poll aggressively forever.

**Fix**: Change the check to `get_sidecar_port() is not None`:

```python
# Before
if sidecar_client.get_sidecar_client() is not None:
    await asyncio.sleep(30)
    continue

# After
if sidecar_client.get_sidecar_port() is not None:
    await asyncio.sleep(30)
    continue
```

### 4. Test files — update delegation tests

Tests that manipulate `get_sidecar_client`/`set_sidecar_client` to test the
cached-client delegation flow need rework to test `call_sidecar_once` instead:

- `test_safe_tool_delegation.py` — mock `call_sidecar_once` return values
- `test_lazy_bridge_integration.py` — update sidecar delegation assertions
- `test_sidecar_monitor.py` — update heartbeat backoff assertions

## What does NOT change

- Port discovery (`_sidecar_monitor`, `read_port_file`, `set_sidecar_port`)
- Bridge mode (`bridge.py`) — completely separate code path
- Local fallback path in `safe_tool`
- `_cleanup_sidecar` — kept for any remaining cached-client cleanup paths
  (e.g., `__main__.py` restart retry)

## Error handling

| Failure | Behavior |
|---|---|
| Connection fails | `call_sidecar_once` returns `None` → local fallback |
| Tool call timeout | `asyncio.TimeoutError` caught → `None` → local fallback |
| Tool call error | `Exception` caught → `None` → local fallback |
| Cleanup | Handled by `async with` context managers — deterministic, no background tasks |

## Trade-offs

- ~40ms overhead per call (connection setup), reduced to ~20-30ms with
  `list_tools()` caching. Acceptable for correctness.
- Up to `max_concurrent_tools` (default 4) simultaneous connections to the
  sidecar under concurrent load. Uvicorn handles this fine.
- Global `_sidecar_client` cache becomes unused in the hot path. Kept for
  `__main__.py` restart retry; can be removed in a future cleanup.

## Files modified

1. `ivy_lsp/mcp/client.py` — add `call_sidecar_once`, `_cancel_safe_wait_for`
   (moved from tools/), `_list_tools_cache`
2. `ivy_lsp/mcp/tools/__init__.py` — simplify sidecar delegation in `safe_tool`,
   update `_injected_names`, re-export `_cancel_safe_wait_for`
3. `ivy_lsp/mcp/server.py` — fix monitor heartbeat check
4. `tests/test_safe_tool_delegation.py` — update delegation tests
5. `tests/test_lazy_bridge_integration.py` — update sidecar assertions
6. `tests/test_sidecar_monitor.py` — update heartbeat assertions
