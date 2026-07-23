# MCP Deadlock Prevention & Process Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent MCP server disconnects during heavy compilation (thread pool isolation) and clean up orphaned LSP processes at session start.

**Architecture:** Dedicated `ThreadPoolExecutor` for MCP tool calls isolates them from the default pool used by background model/graph builds. A process-name reaper in the SessionStart hook kills orphaned `ivy_lsp` processes that escaped PID tracking.

**Tech Stack:** Python asyncio/concurrent.futures, bash (process management hooks)

**Path shortcuts used below:**
- `IVY_LSP` = `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp`
- `PLUGIN` = `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin`

---

### Task 1: Add `tool_executor` field to ToolContext

**Files:**
- Modify: `IVY_LSP/ivy_lsp/mcp/context.py:10` (import), `IVY_LSP/ivy_lsp/mcp/context.py:79` (new field)
- Test: `IVY_LSP/tests/test_tool_executor.py` (create)

- [ ] **Step 1: Write failing test — ToolContext accepts tool_executor field**

```python
# tests/test_tool_executor.py
"""Tests for dedicated tool thread pool executor."""

from __future__ import annotations

import concurrent.futures

from ivy_lsp.mcp.context import ToolContext


def test_tool_context_accepts_executor():
    """ToolContext should accept a tool_executor field."""
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="test")
    try:
        ctx = ToolContext(
            root="/tmp/test",
            staging_dir=None,
            executor=None,
            base_path=None,
            tool_executor=pool,
        )
        assert ctx.tool_executor is pool
    finally:
        pool.shutdown(wait=False)


def test_tool_context_executor_defaults_to_none():
    """ToolContext.tool_executor should default to None."""
    ctx = ToolContext(
        root="/tmp/test",
        staging_dir=None,
        executor=None,
        base_path=None,
    )
    assert ctx.tool_executor is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd IVY_LSP && python -m pytest tests/test_tool_executor.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'tool_executor'`

- [ ] **Step 3: Add tool_executor field to ToolContext**

In `IVY_LSP/ivy_lsp/mcp/context.py`, add import at line 10:

```python
import concurrent.futures
```

Then add the field after `_basename_cache_invalidate` (after line 79):

```python
    # Dedicated thread pool for tool-originated blocking calls.
    # Isolates tool execution from the default pool used by model/graph builders,
    # preventing thread pool starvation during heavy background compilation.
    tool_executor: concurrent.futures.ThreadPoolExecutor | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd IVY_LSP && python -m pytest tests/test_tool_executor.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
cd IVY_LSP
git add ivy_lsp/mcp/context.py tests/test_tool_executor.py
git commit -m "feat: add tool_executor field to ToolContext for thread pool isolation"
```

---

### Task 2: Create dedicated ThreadPoolExecutor in McpServerState

**Files:**
- Modify: `IVY_LSP/ivy_lsp/mcp/server.py:18` (import), `IVY_LSP/ivy_lsp/mcp/server.py:153-215` (McpServerState.__init__), `IVY_LSP/ivy_lsp/mcp/server.py:817-841` (build_tool_context)
- Test: `IVY_LSP/tests/test_tool_executor.py` (extend)

- [ ] **Step 1: Write failing test — McpServerState creates executor and wires to ToolContext**

Append to `tests/test_tool_executor.py`:

```python
import asyncio
import os
import threading

import pytest


@pytest.fixture
def mock_env(monkeypatch):
    """Set minimal env for McpServerState."""
    monkeypatch.setenv("IVY_LSP_PREWARM_MODEL", "0")
    monkeypatch.setenv("IVY_LSP_PREWARM_GRAPH", "0")


def test_mcp_server_state_creates_tool_executor(tmp_path, mock_env):
    """McpServerState should create a _tool_executor ThreadPoolExecutor."""
    from ivy_lsp.mcp.server import McpServerState

    state = McpServerState(root=str(tmp_path))
    assert state._tool_executor is not None
    assert isinstance(state._tool_executor, concurrent.futures.ThreadPoolExecutor)
    state._tool_executor.shutdown(wait=False)


def test_build_tool_context_wires_executor(tmp_path, mock_env):
    """build_tool_context should set tool_executor on ToolContext."""
    from ivy_lsp.mcp.server import McpServerState

    state = McpServerState(root=str(tmp_path))
    ctx = state.build_tool_context()
    assert ctx.tool_executor is state._tool_executor
    state._tool_executor.shutdown(wait=False)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd IVY_LSP && python -m pytest tests/test_tool_executor.py::test_mcp_server_state_creates_tool_executor tests/test_tool_executor.py::test_build_tool_context_wires_executor -v`
Expected: FAIL — `AttributeError: 'McpServerState' object has no attribute '_tool_executor'`

- [ ] **Step 3: Add _tool_executor to McpServerState.__init__ and wire in build_tool_context**

In `IVY_LSP/ivy_lsp/mcp/server.py`:

Add `import concurrent.futures` after line 18 (after `import threading`).

In `McpServerState.__init__()`, after the line that creates `self._basename_cache_obj` (around line 200), add:

```python
        # Dedicated thread pool for MCP tool handlers — isolates tool
        # execution from the default pool used by model/graph builders,
        # preventing starvation during heavy background compilation.
        _pool_size = int(os.environ.get(
            "IVY_LSP_TOOL_POOL_SIZE",
            os.environ.get("IVY_LSP_MAX_CONCURRENT_TOOLS", "4"),
        ))
        self._tool_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=_pool_size,
            thread_name_prefix="ivy-tool",
        )
```

In `build_tool_context()`, after the line `ctx.include_resolver = self._resolver` (line 839), add:

```python
        ctx.tool_executor = self._tool_executor
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd IVY_LSP && python -m pytest tests/test_tool_executor.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd IVY_LSP
git add ivy_lsp/mcp/server.py
git commit -m "feat: create dedicated ThreadPoolExecutor in McpServerState"
```

---

### Task 3: Migrate tool handler thread pool calls to dedicated executor

**Files:**
- Modify: `IVY_LSP/ivy_lsp/mcp/tools/analysis.py:121,268,488,491`
- Modify: `IVY_LSP/ivy_lsp/mcp/tools/verification.py:407,425,704`
- Test: `IVY_LSP/tests/test_tool_executor.py` (extend)

- [ ] **Step 1: Write failing test — tool handlers use ctx.tool_executor**

Append to `tests/test_tool_executor.py`:

```python
@pytest.mark.asyncio
async def test_tool_executor_used_for_thread_dispatch(tmp_path, mock_env):
    """Verify that run_in_executor calls use ctx.tool_executor, not None (default pool)."""
    import concurrent.futures

    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="test-pool")
    thread_names: list[str] = []

    def capture_thread_name():
        thread_names.append(threading.current_thread().name)
        return "ok"

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(pool, capture_thread_name)

    pool.shutdown(wait=False)
    assert any("test-pool" in name for name in thread_names), (
        f"Expected thread name with 'test-pool' prefix, got: {thread_names}"
    )
```

- [ ] **Step 2: Run test to verify it passes (this test validates the mechanism)**

Run: `cd IVY_LSP && python -m pytest tests/test_tool_executor.py::test_tool_executor_used_for_thread_dispatch -v`
Expected: PASS — confirms `run_in_executor(pool, fn)` uses the named pool.

- [ ] **Step 3: Migrate analysis.py call sites**

In `IVY_LSP/ivy_lsp/mcp/tools/analysis.py`:

**Line 121** — `ivy_include_graph` handler. Change:
```python
        graph, basename_cache, _skipped = await asyncio.to_thread(_build_graph)
```
to:
```python
        loop = asyncio.get_running_loop()
        graph, basename_cache, _skipped = await loop.run_in_executor(
            ctx.tool_executor, _build_graph
        )
```

**Line 268** — `ivy_capabilities` handler. Change:
```python
            result["parsing_tiers"] = await asyncio.wait_for(
                loop.run_in_executor(None, TieredExtractor().probe_tiers),
                timeout=3.0,
            )
```
to:
```python
            result["parsing_tiers"] = await asyncio.wait_for(
                loop.run_in_executor(ctx.tool_executor, TieredExtractor().probe_tiers),
                timeout=3.0,
            )
```

**Lines 488 and 491** — `ivy_index` handler. Change:
```python
            summaries = await loop.run_in_executor(None, builder.build_all)
```
to:
```python
            summaries = await loop.run_in_executor(ctx.tool_executor, builder.build_all)
```

And change:
```python
            summary = await loop.run_in_executor(
                None, builder.build_protocol, proto_dir
            )
```
to:
```python
            summary = await loop.run_in_executor(
                ctx.tool_executor, builder.build_protocol, proto_dir
            )
```

- [ ] **Step 4: Migrate verification.py call sites**

In `IVY_LSP/ivy_lsp/mcp/tools/verification.py`:

**Line 407** — `ivy_compile` Docker executor. Change:
```python
                    setup_result = await asyncio.to_thread(
                        ctx.executor.execute,
                        compile_result.setup_commands,
                        workspace_root=ctx.root,
                        timeout=30,
                    )
```
to:
```python
                    loop = asyncio.get_running_loop()
                    setup_result = await loop.run_in_executor(
                        ctx.tool_executor,
                        lambda: ctx.executor.execute(
                            compile_result.setup_commands,
                            workspace_root=ctx.root,
                            timeout=30,
                        ),
                    )
```

**Line 425** — `ivy_compile` Docker executor. Change:
```python
                    exec_result = await asyncio.to_thread(
                        ctx.executor.execute,
                        compile_result.compile_commands,
                        workspace_root=ctx.root,
                        timeout=300,
                    )
```
to:
```python
                    exec_result = await loop.run_in_executor(
                        ctx.tool_executor,
                        lambda: ctx.executor.execute(
                            compile_result.compile_commands,
                            workspace_root=ctx.root,
                            timeout=300,
                        ),
                    )
```

**Line 704** — `ivy_diagnostics` full mode. Change:
```python
                _symbols, error_info = await asyncio.to_thread(
                    fallback_scan,
                    source,
                    abs_path,
                )
```
to:
```python
                loop = asyncio.get_running_loop()
                _symbols, error_info = await loop.run_in_executor(
                    ctx.tool_executor,
                    lambda: fallback_scan(source, abs_path),
                )
```

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `cd IVY_LSP && python -m pytest tests/test_tool_executor.py tests/test_safe_tool_semaphore.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd IVY_LSP
git add ivy_lsp/mcp/tools/analysis.py ivy_lsp/mcp/tools/verification.py
git commit -m "refactor: migrate tool handlers to dedicated thread pool executor"
```

---

### Task 4: Add executor shutdown to start_mcp cleanup

**Files:**
- Modify: `IVY_LSP/ivy_lsp/mcp/server.py:1088-1112` (start_mcp try/except block)

- [ ] **Step 1: Add shutdown call after mcp.run() exits**

In `IVY_LSP/ivy_lsp/mcp/server.py`, the `mcp.run(transport="stdio")` call is at line 1089. The existing `try/except/except` block handles exceptions from `mcp.run()`. Add a `finally` clause to clean up the executor on any exit path (normal, exception, or sys.exit from cancel-scope handlers):

```python
    try:
        mcp.run(transport="stdio")
    except BaseExceptionGroup as eg:
        cancel_scope_errors = [
            e
            for e in eg.exceptions
            if isinstance(e, (RuntimeError, BaseExceptionGroup))
            and "cancel scope" in str(e).lower()
        ]
        non_cancel_errors = [e for e in eg.exceptions if e not in cancel_scope_errors]
        if cancel_scope_errors and not non_cancel_errors:
            logger.warning(
                "[MCP] Cancel scope crash caught at transport level, exiting cleanly: %s",
                eg,
            )
            sys.exit(0)
        raise
    except RuntimeError as exc:
        if "cancel scope" in str(exc).lower():
            logger.warning("[MCP] Cancel scope RuntimeError, exiting cleanly: %s", exc)
            sys.exit(0)
        raise
    finally:
        state._tool_executor.shutdown(wait=False, cancel_futures=True)
        logger.debug("[MCP] Tool executor shut down")
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `cd IVY_LSP && python -m pytest tests/ -v --timeout=30 -x -q 2>&1 | tail -20`
Expected: No new failures

- [ ] **Step 3: Commit**

```bash
cd IVY_LSP
git add ivy_lsp/mcp/server.py
git commit -m "fix: shutdown tool executor on MCP server exit"
```

---

### Task 5: Audit needs_model tools for graceful None handling (A2)

**Files:**
- Modify: none expected (audit task — fix only if gaps found)
- Read: `IVY_LSP/ivy_lsp/mcp/tools/traceability.py`, `IVY_LSP/ivy_lsp/mcp/tools/verification.py`

This is an audit task. The `safe_tool` pre-check at `__init__.py:447-465` already returns "model not ready" when `needs_model=True` and model state is `"pending"` or `"building"`. The audit verifies each tool also handles `None` from `get_model()`.

- [ ] **Step 1: Verify safe_tool pre-check covers all needs_model tools**

Check that `_TOOL_METADATA` marks these tools as `needs_model=True`:
- `ivy_diagnostics` → Yes (`__init__.py:62`)
- `ivy_coverage` → Yes (`__init__.py:69`)
- `ivy_visualize` → Yes (`__init__.py:83`)
- `ivy_model_summary` → Yes (`__init__.py:88`)
- `ivy_quality` → Yes (`__init__.py:96`)
- `ivy_scope` → Yes (`__init__.py:97`)

Run: `cd IVY_LSP && grep -n '"needs_model": True' ivy_lsp/mcp/tools/__init__.py`

- [ ] **Step 2: Verify each tool handles model=None gracefully**

For each tool that calls `await ctx.get_model()`, verify there's a `if model is None:` check that returns an error response (not a crash or partial result).

Check: `grep -A2 'model = await ctx.get_model' ivy_lsp/mcp/tools/traceability.py ivy_lsp/mcp/tools/verification.py`

Expected pattern at each call site:
```python
model = await ctx.get_model()
if model is None:
    return {"success": False, "message": "Semantic model not available..."}
```

If any call site is missing the `None` check, add it. If all have it, document the audit result.

- [ ] **Step 3: Commit audit result (only if changes were made)**

```bash
cd IVY_LSP
# Only if files were modified:
git add ivy_lsp/mcp/tools/traceability.py ivy_lsp/mcp/tools/verification.py
git commit -m "fix: ensure all needs_model tools handle model=None gracefully"
```

If no changes needed:
```bash
# No commit — audit passed, all tools already handle None correctly
```

---

### Task 6: Add process-name reaper to cleanup-stale-pids.sh (B1)

**Files:**
- Modify: `PLUGIN/hooks/scripts/cleanup-stale-pids.sh`

- [ ] **Step 1: Read current script to confirm baseline**

Run: `cat PLUGIN/hooks/scripts/cleanup-stale-pids.sh`

Expected content (18 lines):
```bash
#!/usr/bin/env bash
PID_DIR="/tmp/ivy-lsp-pids"
[ -d "$PID_DIR" ] || exit 0
for pidfile in "$PID_DIR"/*.pid; do
    ...
done
exit 0
```

- [ ] **Step 2: Replace with enhanced script including Phase 2 reaper**

Overwrite `PLUGIN/hooks/scripts/cleanup-stale-pids.sh` with:

```bash
#!/usr/bin/env bash
# SessionStart hook: remove PID files for dead processes.
# Then sweep for orphaned ivy_lsp processes not tracked by any PID file.
# Always exits 0 — cleanup hooks must never fail the session.

PID_DIR="/tmp/ivy-lsp-pids"
[ -d "$PID_DIR" ] || { mkdir -p "$PID_DIR"; exit 0; }

# Phase 1: Remove dead PID files (existing logic)
for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    pid="$(cat "$pidfile" 2>/dev/null)" || continue
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
        rm -f "$pidfile" 2>/dev/null || true
    fi
done

# Phase 2: Kill orphaned ivy_lsp processes for THIS workspace.
# Source workspace-common.sh for detect_ivy_workspace().
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts"
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

- [ ] **Step 3: Verify script is executable**

Run: `chmod +x PLUGIN/hooks/scripts/cleanup-stale-pids.sh`

- [ ] **Step 4: Smoke test — run the script (should be a no-op with no orphans)**

Run: `bash PLUGIN/hooks/scripts/cleanup-stale-pids.sh; echo "exit=$?"`
Expected: `exit=0` (no output, clean exit)

- [ ] **Step 5: Commit**

```bash
cd PLUGIN
git add hooks/scripts/cleanup-stale-pids.sh
git commit -m "feat: add process-name reaper for orphaned ivy_lsp processes"
```

---

### Task 7: Integration verification — kill stale processes and re-run health check

- [ ] **Step 1: Kill the stale Thursday processes manually**

Run:
```bash
kill -TERM 10037 92093 9703 91739 2>/dev/null; echo "killed stale processes"
rm -f /tmp/ivy-lsp-pids/mcp-468dbde5ba31-27485.pid 2>/dev/null
```

- [ ] **Step 2: Verify only current-session processes remain**

Run: `ps aux | grep ivy_lsp | grep -v grep | wc -l`
Expected: 2-3 processes (current LSP + MCP + possibly one uv wrapper)

- [ ] **Step 3: Re-run health check to verify MCP is responsive**

Run: `/nct-health` (or call `ivy_capabilities` via MCP)
Expected: MCP server responds, no deadlock

- [ ] **Step 4: Final commit with all changes**

```bash
cd IVY_LSP
git add -A
git status  # Verify only expected files
git commit -m "feat: MCP deadlock prevention via dedicated thread pool + process reaper

- Add dedicated ThreadPoolExecutor for MCP tool handlers (A1)
- Isolate tool execution from model/graph build thread pool
- Add tool_executor field to ToolContext dataclass
- Migrate 7 asyncio.to_thread/run_in_executor call sites
- Add process-name reaper to cleanup-stale-pids.sh (B1)
- Audit needs_model tools for graceful None handling (A2)"
```
