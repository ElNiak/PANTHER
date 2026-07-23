# Lazy Bridge MCP Architecture

**Date:** 2026-03-20
**Status:** Approved
**Branch:** `refactor/ivy-lsp-cleanup` (worktree: `lsp-to-claude`)

## Problem

The Ivy MCP server fails to start reliably in Claude Code sessions. The current `mcp-bridge` architecture creates a race condition:

1. Claude Code starts the MCP bridge eagerly (session start)
2. The bridge waits 15 seconds for the LSP sidecar's port file
3. The LSP starts lazily (first `.ivy` file access) — port file never appears in time
4. The bridge falls back to standalone MCP, but the combined startup time (~32s) causes Claude Code to kill the process (via orphan detection or stdio timeout)

**Result:** MCP tools (`ivy_capabilities`, `ivy_diagnostics`, `ivy_coverage`, etc.) are never available, even though the plugin's skills, commands, and agents work fine.

## Solution: Lazy Bridge

Replace the blocking `mcp-bridge` mode with a standalone MCP server that upgrades to bridge mode transparently when the LSP sidecar becomes available.

### Architecture

```
Phase 1 (0-10s):   MCP starts standalone → loads .ivy-index/ cache → [MCP-READY]
Phase 2 (background): polls for sidecar port file (2s initially, 10s after 60s)
Phase 3 (transparent): validates workspace match → delegates tools via MCP client → [UPGRADED]
```

The MCP server is **always a standalone stdio MCP server**. The "upgrade" is internal — tool calls are forwarded to the LSP sidecar's MCP HTTP endpoint via an MCP client connection. No stdio relay, no process switching.

```
Claude Code
  ├─ LSP (.lsp.json) → IvyLanguageServer + MCP HTTP sidecar thread
  │                     (starts on first .ivy file access)
  │                     └─ writes /tmp/ivy-mcp-{hash}.port
  │
  └─ MCP (.mcp.json) → standalone MCP (fast start, offline index)
                        └─ background: detects sidecar → upgrades to HTTP delegation
```

### Comparison with current architecture

| Aspect | Current (broken) | New (lazy bridge) |
|--------|-----------------|-------------------|
| `.mcp.json` mode | `mcp-bridge` | `mcp` |
| Startup time | ~32s (killed before ready) | ~10-15s |
| Initial data source | N/A (never starts) | Offline `.ivy-index/` cache |
| Live state sharing | Never achieved | Automatic when LSP sidecar detected |
| Sidecar failure | Fatal (bridge crashes) | Transparent fallback to local |
| Inter-process coupling | Tight (port file + HTTP + stdio relay) | Loose (optional HTTP delegation) |

## Design Details

### 1. Startup Flow

**`.mcp.json` change:**
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
      "env": { ... }
    }
  }
}
```

**`start-ivy-server.sh` changes:**
- Remove the `mcp-bridge` block (lines 93-135) that waits for the sidecar port file
- Remove the `--mode mcp` deprecation notice (lines 29-33) — standalone MCP is now the primary mode
- Remove `mcp-bridge` from the argument validation (line 22)
- The `--mode mcp` launch path (lines 184-192) is unchanged

### 2. Upgrade Mechanism (Tool Delegation via MCP Client)

The existing tool registration uses `FastMCP` with `@mcp.tool()` decorators and a `safe_tool` wrapper in `ivy_lsp/tools/__init__.py`. The upgrade mechanism intercepts at the `safe_tool` level, not at a centralized dispatch point.

**Integration approach:** Modify the `safe_tool` decorator to check a module-level `_sidecar_client` reference. When set, the wrapper short-circuits the local handler and forwards the call to the sidecar via the `mcp` library's client-side `call_tool()` method. The sidecar's response is returned **verbatim** — no local `_format_result` or timeout tracking is applied (the sidecar's own `safe_tool` handles that).

```python
# In mcp_server.py — module-level state
_sidecar_client: Optional[ClientSession] = None  # None = standalone mode

def safe_tool(fn):
    """Decorator wrapping tool handlers with error handling + sidecar delegation."""
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        # Phase 3: delegate to sidecar if available
        client = _sidecar_client
        if client is not None:
            try:
                result = await client.call_tool(fn.__name__, kwargs)
                return result  # verbatim, no local formatting
            except Exception:
                logger.warning("[DOWNGRADED] Sidecar call to %s failed, using local", fn.__name__)
                _set_sidecar_client(None)
                # Fall through to local handling

        # Phase 1: local handling with offline index
        try:
            return _format_result(await fn(*args, **kwargs))
        except Exception as exc:
            return _format_error(exc)
    return wrapper
```

**Background sidecar monitor** (started as `asyncio.create_task()` after MCP initialization):

```python
async def _sidecar_monitor(workspace_root: str):
    """Poll for sidecar port file, validate workspace, upgrade when ready."""
    poll_interval = 2.0  # fast polling for first 60s
    elapsed = 0.0

    while True:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        # Progressive backoff: 2s for first 60s, then 10s
        if elapsed > 60 and poll_interval < 10:
            poll_interval = 10.0

        port = _read_port_file(workspace_root)
        if port is None:
            continue

        # Validate workspace match before upgrading
        if not await _validate_sidecar_workspace(port, workspace_root):
            logger.debug("Sidecar workspace mismatch, skipping")
            continue

        if await _health_check(port):
            client = await _connect_to_sidecar(port)
            if client:
                _set_sidecar_client(client)
                logger.info("[UPGRADED] Delegating to LSP sidecar on port %d", port)
                # Keep polling at slow rate to detect sidecar restarts
                poll_interval = 30.0
```

**Workspace validation:** Before upgrading, the monitor hits the sidecar's `/health` endpoint and compares the returned workspace root against its own. This prevents upgrading to a sidecar from a different session/worktree that happens to use the same workspace hash.

**Key properties:**
- Uses existing `streamablehttp_client` from the `mcp` library (already a dependency)
- Sidecar response is returned verbatim — no double-formatting or double-timeout
- `_set_sidecar_client()` is a simple reference swap (atomic under CPython GIL)
- The monitor validates workspace match before upgrading

### 3. Error Handling

**Sidecar never appears** (user never opens `.ivy` file):
- MCP runs standalone for entire session using offline index
- Background monitor polls at 2s initially, 10s after 60s (low overhead: one file stat)
- This is the common case for short sessions

**Sidecar appears then dies** (LSP crashes):
- `safe_tool` wrapper catches connection errors from sidecar client
- Sets `_sidecar_client = None` → reverts to local handling
- Logs `[DOWNGRADED] Sidecar lost, reverting to local handling`
- Monitor continues polling — will re-upgrade if sidecar restarts

**Post-downgrade degraded results:**
After reverting from sidecar to local handling, model-dependent tools may return degraded results (e.g., `"state": "not_built"`) until the local model prewarm/lazy-build completes. This is expected behavior and self-resolves within seconds as the local model initializes. The degradation window is brief because the offline index is still loaded — only the live SemanticModel needs rebuilding.

**Tool call during upgrade transition:**
- Reference swap is atomic (`_sidecar_client = client`, CPython GIL)
- An in-flight local handler continues to completion on the local path
- The next `safe_tool` invocation reads the new reference and delegates to sidecar
- No locking needed — consistency concern is limited to the brief overlap, not data corruption

**Stale port file from previous session:**
- The sidecar monitor validates the sidecar's workspace root via the `/health` endpoint before upgrading
- If the workspace root doesn't match, the upgrade is skipped
- The `/health` endpoint already returns workspace metadata (added in this design if not present)

**SIGTERM / orphan detection (the original killer):**
- With fast standalone startup (~10s), MCP responds to the initialization handshake well within the 60s timeout
- The orphan watchdog (checks parent PID every 5s) never triggers because the process is healthy and responsive

### 4. File Changes

| File | Change |
|------|--------|
| `.mcp.json` | `--mode mcp-bridge` → `--mode mcp` |
| `start-ivy-server.sh` | Remove `mcp-bridge` block (lines 93-135). Remove deprecation notice for `--mode mcp` (lines 29-33). Remove `mcp-bridge` from argument validation (line 22). |
| `mcp_server.py` | Add `_sidecar_client` module state, `_sidecar_monitor()` background task, workspace validation |
| `tools/__init__.py` | Modify `safe_tool` decorator to check `_sidecar_client` and delegate when set |
| `mcp_sidecar.py` | Ensure `/health` endpoint returns `workspace_root` for validation |
| `mcp_bridge.py` | No changes (kept for backward compat / CI usage) |
| `.lsp.json` | No changes |
| `ivy-lsp-wrapper.sh` | Delete. Only referenced in a comment in `workspace-common.sh` (line 3). No `.lsp.json`, hook, or script uses it. Update the comment. |

### 5. Validation Plan

1. **Fast startup**: Start fresh Claude Code session → MCP tools appear within ~15s
2. **Health check**: Run `/nct-health` → Steps 4-6 (MCP server alive, Workspace access, Model builds) PASS
3. **Upgrade detection**: Open an `.ivy` file (triggers LSP + sidecar) → check MCP log for `[UPGRADED]` message
4. **Fallback resilience**: Kill the LSP → next MCP tool call works locally with `[DOWNGRADED]` in log
5. **Clean session**: No stale PID or port files accumulate across sessions
6. **Wrong-workspace rejection**: Start two worktree sessions → verify MCP does not upgrade to the other session's sidecar

### 6. Rollback Strategy

**Full rollback** (restore original bridge behavior): Revert both `.mcp.json` (back to `--mode mcp-bridge`) AND `start-ivy-server.sh` (restore the `mcp-bridge` argument validation and wait/fallback block). Both changes are required — reverting only `.mcp.json` without restoring the shell script's `mcp-bridge` handling will fail at argument validation. `mcp_bridge.py` is preserved in the ivy-lsp package for this purpose.

**Lightweight disable** (keep standalone, skip upgrade): Set env var `IVY_MCP_DISABLE_UPGRADE=1` to skip the sidecar monitor entirely. MCP stays standalone for the whole session. No code revert needed.

## Constraints

- The MCP timeout in Claude Code defaults to 60 seconds (`MCP_TIMEOUT` env var, in milliseconds). Configurable but timeouts >60s may not be respected reliably.
- The offline `.ivy-index/` cache must be reasonably fresh. The index is built by the `ivy_lsp index` CLI command and/or the LSP server's indexing pipeline. Stale index means stale MCP results until upgrade.
- A few seconds of staleness between LSP edits and MCP tool results is acceptable (confirmed by user).

## Out of Scope

- Removing `mcp_bridge.py` entirely (kept for backward compat / rollback)
- Changing the LSP startup behavior (remains lazy, on-demand)
- Modifying the offline index format or update mechanism
- Addressing the uvx build-from-source latency (orthogonal optimization)
