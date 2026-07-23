# MCP Deadlock Prevention & Process Lifecycle Management

**Date**: 2026-03-27
**Status**: Draft
**Scope**: ivy-lsp submodule + panther-ivy-plugin scripts

## Problem Statement

Two related issues degrade Ivy LSP + MCP reliability:

### A. MCP Server Deadlock During Heavy Compilation

The MCP server disconnects when tool calls (e.g., `ivy_diagnostics`) arrive while a background model build or compilation is running. Root cause: **thread pool starvation**.

**Mechanism:**
1. Model build (`_build_model`) runs via `asyncio.to_thread()` on Python's default `ThreadPoolExecutor`
2. Tool call arrives, also needs `asyncio.to_thread()` for its own work
3. Default thread pool is saturated by compilation workers
4. Tool call's `asyncio.to_thread()` queues indefinitely
5. Tool timeout (120s) fires, `_cancel_safe_wait_for()` cancels the child task
6. Cancellation propagates to MCP transport, severing the connection
7. No ERROR/CRITICAL in log — it's a clean transport-level disconnect

The existing crash shield (commit `767cd60`) catches `RuntimeError` from cancel-scope races but does not address thread pool exhaustion.

**Evidence:**
- Health check: `ivy_diagnostics` call caused MCP disconnect while compilation was at 228/341 files
- Log shows continuous compilation progress notifications via pygls at time of disconnect
- No error entries in log — confirms transport-level (not application-level) failure

### B. Stale Process Accumulation

Orphan `ivy_lsp` processes from previous sessions persist indefinitely. The current cleanup system is purely PID-file-based and cannot detect processes that:
- Predate the PID tracking system
- Lost their PID files (crash without EXIT trap)
- Were spawned by a different mechanism

**Evidence:**
- 4 processes from Thursday still running (PIDs 10037, 92093 + their uv wrappers 9703, 91739)
- None have corresponding PID files in `/tmp/ivy-lsp-pids/`
- Combined: 34+ minutes CPU time consumed by stale LSP, 55s by stale MCP server

## Design

### Fix A1: Dedicated Thread Pool for MCP Tool Execution

**Goal:** Isolate MCP tool calls from background model build/compilation so that heavy compilation can never starve tool call execution.

**Change:** Create a dedicated `ThreadPoolExecutor` for tool-originated `asyncio.to_thread()` calls, separate from the default pool used by model building.

#### File: `ivy_lsp/mcp/server.py`

Add a dedicated executor to `McpServerState.__init__()`:

```python
import concurrent.futures

class McpServerState:
    # New: dedicated thread pool for tool calls (separate from model build)
    _TOOL_POOL_SIZE = 4  # Match IVY_LSP_MAX_CONCURRENT_TOOLS default

    def __init__(self, ...):
        ...
        # Dedicated tool thread pool — model builds use the default pool
        self._tool_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self._TOOL_POOL_SIZE,
            thread_name_prefix="ivy-tool",
        )
```

The model builders continue using the default pool via bare `asyncio.to_thread()`:
```python
# Unchanged — model build uses default pool
self._model_builder = LazyAsyncBuilder(
    lambda: asyncio.to_thread(self._build_model),  # default pool
    ...
)
```

#### File: `ivy_lsp/mcp/context.py`

Add `tool_executor` field to the `ToolContext` dataclass (line 55):

```python
@dataclass
class ToolContext:
    ...
    # Dedicated thread pool for tool-originated blocking calls.
    # Avoids contending with the default pool used by model/graph builders.
    tool_executor: concurrent.futures.ThreadPoolExecutor | None = None
```

#### File: `ivy_lsp/mcp/server.py` (in `start_mcp()`)

Wire the executor into `ToolContext` construction:

```python
ctx = ToolContext(
    ...
    tool_executor=state._tool_executor,
)
```

#### File: `ivy_lsp/mcp/tools/analysis.py` (and other tool modules)

Replace `asyncio.to_thread(...)` and `loop.run_in_executor(None, ...)` calls in tool handlers with the dedicated executor:

```python
# Before (uses default pool — contends with model build):
graph, basename_cache, _skipped = await asyncio.to_thread(_build_graph)

# After (uses dedicated tool pool):
loop = asyncio.get_running_loop()
graph, basename_cache, _skipped = await loop.run_in_executor(
    ctx.tool_executor, _build_graph
)
```

**Call sites to change** (all in `ivy_lsp/mcp/tools/`):
- `analysis.py:121` — `_build_graph` in `ivy_include_graph`
- `analysis.py:268` — `TieredExtractor().probe_tiers` in `ivy_diagnostics`
- `analysis.py:488` — `builder.build_all` in `ivy_model_summary`
- `analysis.py:491` — `builder.build_for_action` in `ivy_model_summary`
- `verification.py:407` — `setup_result` in `ivy_verify`
- `verification.py:425` — `exec_result` in `ivy_verify`
- `verification.py:704` — `_symbols, error_info` in `ivy_diagnostics` (full mode)

**Not changed** (intentionally left on default pool):
- `server.py:179` — `_build_model` (this IS the heavy build, it stays on the default pool)
- `server.py:189` — `_build_requirement_graph` (same)
- `client.py:82` — `_fetch_health_sync` (lightweight, fine on default)

**Shutdown:** Add cleanup in `start_mcp()` teardown:

```python
# In start_mcp() cleanup
state._tool_executor.shutdown(wait=False, cancel_futures=True)
```

#### Configuration

The pool size should be configurable via environment variable, defaulting to `IVY_LSP_MAX_CONCURRENT_TOOLS`:

```python
_TOOL_POOL_SIZE = int(os.environ.get(
    "IVY_LSP_TOOL_POOL_SIZE",
    os.environ.get("IVY_LSP_MAX_CONCURRENT_TOOLS", "4"),
))
```

### Fix A2: "Model Busy" Fast-Fail (Already Partially Implemented)

The code at `tools/__init__.py:447-465` already implements a "model not ready" check — but it only fires when `ctx.semantic_model is None` AND `get_model_status()` reports `"pending"` or `"building"`.

**Gap:** When the model IS being built via `LazyAsyncBuilder`, `get()` returns `None` immediately (line 109-110: "Another coroutine is building — don't queue up"). But the tool handler may then proceed WITHOUT the model and produce incomplete/wrong results, rather than returning the "not ready" response.

**Change:** Ensure `needs_model` tools always check `get_model_status()` BEFORE calling `get_model()`, and return the "not ready" response if the model is still building. The current implementation's ordering looks correct, but we should verify that ALL paths through tool handlers that need the model go through the `ctx.get_model()` method which respects this check.

**Verification task:** Audit each `needs_model=True` tool to confirm it calls `ctx.get_model()` (not `ctx.semantic_model` directly) and handles `None` return gracefully.

Tools with `needs_model=True`:
- `ivy_diagnostics` (mode=full)
- `ivy_coverage`
- `ivy_visualize`
- `ivy_model_summary`
- `ivy_quality`
- `ivy_scope`

### Fix B1: Process-Name Reaper at SessionStart

**Goal:** Kill orphaned `ivy_lsp` processes for the current workspace that aren't tracked by PID files.

#### File: `hooks/scripts/cleanup-stale-pids.sh`

Add a process-name sweep AFTER the existing dead-PID-file cleanup.

**Hook ordering note:** `cleanup-stale-pids.sh` runs BEFORE `detect-ivy-workspace.sh` in the SessionStart hook sequence. Therefore, `DETECTED_ROOT` is not yet set by the detect script. Phase 2 must detect the workspace root independently by sourcing `workspace-common.sh` (same utility used by `start-ivy-server.sh`).

```bash
#!/usr/bin/env bash
# SessionStart hook: remove PID files for dead processes.
# Then sweep for orphaned ivy_lsp processes not tracked by any PID file.
# Always exits 0 — cleanup hooks must never fail the session.

PID_DIR="/tmp/ivy-lsp-pids"
[ -d "$PID_DIR" ] || { mkdir -p "$PID_DIR"; exit 0; }

# Phase 1: Remove dead PID files (existing logic, unchanged)
for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    pid="$(cat "$pidfile" 2>/dev/null)" || continue
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
        rm -f "$pidfile" 2>/dev/null || true
    fi
done

# Phase 2: Kill orphaned ivy_lsp processes for THIS workspace.
# Source workspace-common.sh for detect_ivy_workspace().
# CLAUDE_PLUGIN_ROOT is set by Claude Code for plugin hooks.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../scripts" && pwd)"
if [ -f "$SCRIPT_DIR/workspace-common.sh" ]; then
    # shellcheck source=../scripts/workspace-common.sh
    source "$SCRIPT_DIR/workspace-common.sh"
    detect_ivy_workspace 2>/dev/null || true
fi

# Fallback: try env vars if detect failed
DETECTED_ROOT="${DETECTED_ROOT:-${IVY_WORKSPACE_ROOT:-${IVY_LSP_WORKSPACE:-}}}"
[ -z "$DETECTED_ROOT" ] && exit 0

# Collect PIDs of tracked (live) processes
tracked_pids=""
for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    pid="$(cat "$pidfile" 2>/dev/null)" || continue
    tracked_pids="$tracked_pids $pid"
done

# Find all ivy_lsp processes whose command line contains our workspace root.
# Use ps + grep instead of pgrep for broader compatibility.
for pid in $(ps -eo pid,args 2>/dev/null | grep "[i]vy_lsp" | grep "$DETECTED_ROOT" | awk '{print $1}'); do
    # Skip if this PID is tracked
    case " $tracked_pids " in
        *" $pid "*) continue ;;
    esac
    # Skip our own PID
    [ "$pid" = "$$" ] && continue
    # Kill orphan
    echo "[cleanup-stale-pids] Killing orphaned ivy_lsp process: PID=$pid" >&2
    kill -TERM "$pid" 2>/dev/null || true
done

exit 0
```

**Key design decisions:**
- **Self-contained workspace detection:** Sources `workspace-common.sh` to find the workspace root, since this hook runs before `detect-ivy-workspace.sh`. Falls back to `IVY_WORKSPACE_ROOT` / `IVY_LSP_WORKSPACE` env vars if sourcing fails.
- **Workspace-scoped:** Only kills processes whose command line contains `$DETECTED_ROOT`. This prevents killing LSP instances for other worktrees.
- **Tracked-PID-aware:** Skips any PID that has a corresponding PID file (those are managed by start-ivy-server.sh).
- **Uses `ps -eo pid,args` instead of `pgrep`:** More portable across macOS/Linux, avoids the `sysmon` sandbox issue seen during health check.
- **Kills uv wrappers too:** The `grep ivy_lsp` pattern matches both the Python process and the uv wrapper (both contain "ivy_lsp" in their args).
- **Always exits 0:** Cleanup must never block session startup.

#### File: `scripts/start-ivy-server.sh`

No changes needed. The existing workspace-scoped PID cleanup (lines 117-136) already handles the "kill old server for this workspace" case. Fix B1 adds a safety net for processes that escaped PID tracking entirely.

## Files Changed

| File | Change | Subsystem |
|------|--------|-----------|
| `ivy_lsp/mcp/server.py` | Add `_tool_executor` ThreadPoolExecutor to McpServerState, wire to ToolContext | ivy-lsp |
| `ivy_lsp/mcp/context.py` | Add `tool_executor` field to ToolContext dataclass | ivy-lsp |
| `ivy_lsp/mcp/tools/analysis.py` | Use `ctx.tool_executor` for thread pool calls | ivy-lsp |
| `ivy_lsp/mcp/tools/verification.py` | Use `ctx.tool_executor` for thread pool calls | ivy-lsp |
| `hooks/scripts/cleanup-stale-pids.sh` | Add Phase 2: process-name reaper with self-contained workspace detection | panther-ivy-plugin |

## Testing

### A1: Dedicated Thread Pool
- **Unit test:** Mock `ThreadPoolExecutor`, verify tool calls use the dedicated pool while model build uses the default
- **Integration test:** Start MCP server, trigger model build, call `ivy_diagnostics` concurrently — verify the tool call completes (no disconnect)
- **Stress test:** Call 4 tools simultaneously during model build — all should complete within timeout

### A2: Model Busy Check
- **Unit test:** For each `needs_model=True` tool, verify it returns the "model not ready" response when `get_model_status()` returns `"building"`
- **Unit test:** Verify tools return meaningful results (not empty/partial) when model IS available

### B1: Process Reaper
- **Manual test:** Start an ivy_lsp process without PID tracking, start a new session, verify the orphan is killed
- **Safety test:** Start two worktrees with different workspaces, verify reaper in workspace A doesn't kill processes in workspace B
- **Idempotency test:** Run cleanup-stale-pids.sh twice — second run should be a no-op

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Dedicated pool adds memory overhead | Pool is small (4 threads). Shutdown on server exit. |
| `ps -eo pid,args` grep may match unrelated processes | Scoped by `$DETECTED_ROOT` path. The path is specific enough to avoid false positives. |
| Killing uv wrapper but not child, or vice versa | Both contain "ivy_lsp" in args and are matched. Process group kill isn't needed because uv uses `exec` (same PID). |
| Model build and tool calls both need same resources (e.g., file locks) | `_cached_ivy_files_lock` is a `threading.Lock` that's held briefly. Thread pool separation doesn't create new lock contention. |

## Out of Scope

- **Thread pool sizing for model build**: The default pool is adequate for the model builder. The problem is only that tool calls share it.
- **MCP SDK upstream fix**: The cancel-scope race (MCP SDK #577) is already mitigated by the crash shield. This design addresses a different failure mode.
- **Process group tracking (Approach B2)**: Deferred — the `setsid` approach is more invasive and may break stdio transport.
- **Heartbeat system (Approach B3)**: Deferred — requires server-side changes for something the shell reaper handles.
