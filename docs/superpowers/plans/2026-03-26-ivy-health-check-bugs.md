# Ivy LSP + MCP Health Check Bug Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 bugs discovered during the Ivy LSP + MCP 21-step health check: MCP semaphore deadlock, workspaceSymbol returning wrong files, documentSymbol false "indexing" status, and workspace state clearing mid-session. Plus circuit breaker reset hardening.

**Architecture:** All changes are in the ivy-lsp submodule at `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`. Each bug fix is independent — one file per bug (except Bug 1 which touches 3 files). Test files follow the existing pattern in `tests/`.

**Tech Stack:** Python 3.10+, asyncio, lsprotocol, pytest with asyncio_mode="auto"

**Base directory for all relative paths:** `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`

---

### Task 1: Fix MCP semaphore deadlock (Bug 1a)

**Files:**
- Modify: `ivy_lsp/mcp/tools/__init__.py:418-421`
- Test: `tests/test_safe_tool_semaphore.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_safe_tool_semaphore.py`:

```python
"""Tests for safe_tool semaphore acquisition timeout."""

from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_semaphore_acquisition_times_out():
    """When all semaphore slots are exhausted, new calls should time out
    rather than blocking forever."""
    sem = asyncio.Semaphore(1)

    # Exhaust the single slot
    await sem.acquire()

    # Attempting to acquire with a timeout should raise TimeoutError
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(sem.acquire(), timeout=0.1)

    # Release the slot so cleanup is clean
    sem.release()


@pytest.mark.asyncio
async def test_semaphore_releases_on_tool_timeout():
    """After a tool times out, the semaphore slot must be released
    so subsequent calls can proceed."""
    sem = asyncio.Semaphore(1)

    # Simulate: acquire, then release in finally block
    try:
        await asyncio.wait_for(sem.acquire(), timeout=0.5)
        # Simulate a tool that hangs
        await asyncio.wait_for(asyncio.sleep(10), timeout=0.1)
    except asyncio.TimeoutError:
        pass
    finally:
        sem.release()

    # Semaphore should be available again
    acquired = sem.locked()
    assert not acquired, "Semaphore should be free after release"
```

- [ ] **Step 2: Run test to verify it passes (these test the pattern, not the bug)**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_safe_tool_semaphore.py -v`
Expected: PASS (these verify the timeout pattern works)

- [ ] **Step 3: Apply the semaphore timeout fix**

In `ivy_lsp/mcp/tools/__init__.py`, replace lines 418-421:

```python
# OLD:
            async with sem:
                result = await _cancel_safe_wait_for(
                    fn(*args, **kwargs), timeout=timeout
                )
```

With:

```python
# NEW:
            sem_timeout = timeout * 0.5
            try:
                await asyncio.wait_for(sem.acquire(), timeout=sem_timeout)
            except asyncio.TimeoutError:
                metrics.timeout_count += 1
                metrics.error_count += 1
                logger.error(
                    "MCP tool %s timed out waiting for concurrency slot (%.1fs)",
                    tool_name,
                    sem_timeout,
                )
                return _error_result(
                    {
                        "success": False,
                        "message": f"Tool queued too long (>{sem_timeout:.0f}s). Other tools may be stuck.",
                        "timeout": True,
                        "tool": tool_name,
                    }
                )
            try:
                result = await _cancel_safe_wait_for(
                    fn(*args, **kwargs), timeout=timeout
                )
            finally:
                sem.release()
```

- [ ] **Step 4: Run existing tests to verify no regressions**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -20`
Expected: All existing tests pass.

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp/tools/__init__.py tests/test_safe_tool_semaphore.py
git commit -m "fix: add timeout to MCP semaphore acquisition to prevent deadlock"
```

---

### Task 2: Add per-tier timeout to probe_tiers() (Bug 1b)

**Files:**
- Modify: `ivy_lsp/mcp/tools/analysis.py:271-275`

- [ ] **Step 1: Apply the probe_tiers timeout fix**

In `ivy_lsp/mcp/tools/analysis.py`, replace lines 271-275:

```python
# OLD:
        # Parsing tier availability
        try:
            result["parsing_tiers"] = TieredExtractor().probe_tiers()
        except Exception:
            result["parsing_tiers"] = {"error": "probe failed"}
```

With:

```python
# NEW:
        # Parsing tier availability (capped at 3s to avoid blocking ivy_capabilities)
        try:
            loop = asyncio.get_event_loop()
            result["parsing_tiers"] = await asyncio.wait_for(
                loop.run_in_executor(None, TieredExtractor().probe_tiers),
                timeout=3.0,
            )
        except asyncio.TimeoutError:
            result["parsing_tiers"] = {"error": "probe timed out (3s)"}
        except Exception:
            result["parsing_tiers"] = {"error": "probe failed"}
```

Also add at the top of the file if not already present:

```python
import asyncio
```

- [ ] **Step 2: Verify asyncio import exists**

Run: `grep -n "^import asyncio" ivy_lsp/mcp/tools/analysis.py`

If not found, add `import asyncio` after the existing imports.

- [ ] **Step 3: Run tests to verify no regressions**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -20`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp/tools/analysis.py
git commit -m "fix: add 3s timeout to TieredExtractor.probe_tiers() in ivy_capabilities"
```

---

### Task 3: Reset circuit breaker on MCP startup (Bug 1c)

**Files:**
- Modify: `ivy_lsp/mcp/server.py:813` (after MCP startup log, before workspace scoping)

- [ ] **Step 1: Apply the circuit breaker reset**

In `ivy_lsp/mcp/server.py`, after line 821 (after the "MCP startup initialized" log), insert:

```python
        # Reset stale circuit breaker state from previous sessions.
        # The health-check hook at check-mcp-health.py persists failure
        # counts to /tmp/ivy-mcp-health-state.json. If that file is stale
        # (>60s old), clear it so a fresh MCP server doesn't inherit old
        # failures.
        _cb_state_file = "/tmp/ivy-mcp-health-state.json"
        try:
            if os.path.exists(_cb_state_file):
                import json as _json
                _cb_mtime = os.path.getmtime(_cb_state_file)
                if time.time() - _cb_mtime > 60:
                    with open(_cb_state_file, "w") as _cb_f:
                        _json.dump(
                            {"consecutive_failures": 0, "last_update": time.time()},
                            _cb_f,
                        )
                    logger.info("Reset stale circuit breaker state (age=%.0fs)", time.time() - _cb_mtime)
        except OSError:
            pass  # Best-effort; state file is optional
```

- [ ] **Step 2: Verify `time` and `os` are already imported**

Run: `head -30 ivy_lsp/mcp/server.py | grep -E "^import (time|os)"`

Both should already be imported. If `time` is missing, add `import time` to the imports.

- [ ] **Step 3: Run tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -20`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp/server.py
git commit -m "fix: reset stale circuit breaker state on MCP server startup"
```

---

### Task 4: Fix workspaceSymbol protocol scoping (Bug 2)

**Files:**
- Modify: `ivy_lsp/lsp/workspace_symbols.py:191` (add protocol filter after workspace filter)
- Test: `tests/test_workspace_symbols_filtering.py` (add new test class)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_workspace_symbols_filtering.py`:

```python
class TestWorkspaceSymbolsProtocolScopingFromFilepath:
    """When workspace is not active but active_filepath is set,
    symbols should be scoped to the protocol derived from the filepath."""

    def test_protocol_scoping_filters_to_quic(self):
        """active_filepath in quic/ should filter out patterns/ and apt/ symbols."""
        quic_file = os.path.normpath(
            os.path.abspath("/ws/protocol-testing/quic/quic_stack/quic_types.ivy")
        )
        pattern_file = os.path.normpath(
            os.path.abspath("/ws/protocol-testing/patterns/shims/shim_tcp_template.ivy")
        )
        apt_file = os.path.normpath(
            os.path.abspath("/ws/protocol-testing/apt/apt_model.ivy")
        )

        syms = [
            _make_symbol("quic_cid", quic_file),
            _make_symbol("shim_tcp", pattern_file),
            _make_symbol("apt_action", apt_file),
        ]
        indexer = _MockIndexer(syms)

        # No workspace active, but active_filepath points to a quic file
        results = compute_workspace_symbols(
            indexer,
            query="",
            active_filepath=quic_file,
            active_workspace=None,
        )
        names = [r.name for r in results]
        assert "quic_cid" in names
        assert "shim_tcp" not in names
        assert "apt_action" not in names

    def test_protocol_scoping_no_active_filepath_returns_all(self):
        """Without active_filepath, no protocol scoping applied."""
        quic_file = os.path.normpath(
            os.path.abspath("/ws/protocol-testing/quic/quic_stack/quic_types.ivy")
        )
        pattern_file = os.path.normpath(
            os.path.abspath("/ws/protocol-testing/patterns/shims/shim_tcp.ivy")
        )

        syms = [
            _make_symbol("quic_cid", quic_file),
            _make_symbol("shim_tcp", pattern_file),
        ]
        indexer = _MockIndexer(syms)

        results = compute_workspace_symbols(
            indexer,
            query="",
            active_filepath=None,
            active_workspace=None,
        )
        names = [r.name for r in results]
        assert "quic_cid" in names
        assert "shim_tcp" in names

    def test_protocol_scoping_non_protocol_path_returns_all(self):
        """active_filepath without protocol-testing/ segment returns all."""
        random_file = os.path.normpath(os.path.abspath("/ws/other/foo.ivy"))
        quic_file = os.path.normpath(
            os.path.abspath("/ws/protocol-testing/quic/q.ivy")
        )

        syms = [
            _make_symbol("foo_sym", random_file),
            _make_symbol("quic_sym", quic_file),
        ]
        indexer = _MockIndexer(syms)

        results = compute_workspace_symbols(
            indexer,
            query="",
            active_filepath=random_file,
            active_workspace=None,
        )
        names = [r.name for r in results]
        # No protocol-testing/ in path, so no filtering
        assert "foo_sym" in names
        assert "quic_sym" in names

    def test_workspace_filter_takes_precedence_over_protocol_scoping(self):
        """When workspace IS active, workspace filter wins (protocol scoping skipped)."""
        quic_file = os.path.normpath(
            os.path.abspath("/ws/protocol-testing/quic/quic_stack/quic_types.ivy")
        )
        apt_file = os.path.normpath(
            os.path.abspath("/ws/protocol-testing/apt/apt_model.ivy")
        )

        syms = [
            _make_symbol("quic_sym", quic_file),
            _make_symbol("apt_sym", apt_file),
        ]
        file_to_layer = {quic_file: "quic", apt_file: "apt"}
        indexer = _MockIndexer(syms, file_to_layer=file_to_layer)

        ws = ActiveWorkspace(
            active_group="quic",
            active_layers={"quic"},
            active_tests=[],
            granularity="protocol",
            set_by="explicit",
        )

        results = compute_workspace_symbols(
            indexer,
            query="",
            active_filepath=quic_file,
            active_workspace=ws,
        )
        names = [r.name for r in results]
        assert "quic_sym" in names
        assert "apt_sym" not in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_workspace_symbols_filtering.py::TestWorkspaceSymbolsProtocolScopingFromFilepath::test_protocol_scoping_filters_to_quic -v`
Expected: FAIL — `shim_tcp` and `apt_action` are in results (no protocol filtering yet).

- [ ] **Step 3: Implement protocol-scoped filtering**

In `ivy_lsp/lsp/workspace_symbols.py`, add the helper function after the imports (after line 30):

```python
def _derive_protocol_root(filepath: str) -> Optional[str]:
    """Extract the protocol root directory from a file path.

    Looks for ``protocol-testing/<protocol>/`` in the path and returns
    the absolute path up to and including the protocol directory.
    Returns ``None`` if no such segment is found.
    """
    norm = os.path.normpath(os.path.abspath(filepath))
    marker = os.sep + "protocol-testing" + os.sep
    idx = norm.find(marker)
    if idx < 0:
        return None
    after = norm[idx + len(marker):]
    parts = after.split(os.sep)
    if not parts or not parts[0]:
        return None
    return norm[: idx + len(marker) + len(parts[0])]
```

Then in `compute_workspace_symbols()`, after line 190 (after the closing `]` of the workspace filter block), add:

```python
    elif active_filepath:
        # No workspace active — derive protocol scope from active file.
        protocol_root = _derive_protocol_root(active_filepath)
        if protocol_root:
            flat = [
                f
                for f in flat
                if f.file_path
                and os.path.normpath(os.path.abspath(f.file_path)).startswith(
                    protocol_root
                )
            ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_workspace_symbols_filtering.py -v`
Expected: ALL tests pass (existing + new).

- [ ] **Step 5: Run full test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -20`
Expected: No regressions.

- [ ] **Step 6: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/lsp/workspace_symbols.py tests/test_workspace_symbols_filtering.py
git commit -m "fix: scope workspaceSymbol results to active protocol when no workspace set"
```

---

### Task 5: Fix documentSymbol false "indexing" status (Bug 3)

**Files:**
- Modify: `ivy_lsp/lsp/document_symbols.py:209-213`

- [ ] **Step 1: Apply the indexer readiness fix**

In `ivy_lsp/lsp/document_symbols.py`, replace lines 209-213:

```python
# OLD:
            if not result and source.strip():
                initializing = bool(getattr(server, "initializing", False))
                parser_available = parser is not None
                indexer_available = indexer is not None
                if initializing:
```

With:

```python
# NEW:
            if not result and source.strip():
                parser_available = parser is not None
                indexer_available = indexer is not None
                # Check actual data readiness rather than protocol init flag.
                # The server.initializing flag reflects LSP protocol state, not
                # indexer readiness — other ops (hover, goToDefinition) work fine
                # during late init because the indexer is already functional.
                indexer_has_data = (
                    indexer_available
                    and hasattr(indexer, "_symbol_table")
                    and len(indexer._symbol_table._all) > 0
                )
                if not indexer_has_data and not parser_available:
```

- [ ] **Step 2: Run tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -20`
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/lsp/document_symbols.py
git commit -m "fix: check indexer data readiness instead of protocol init flag for documentSymbol"
```

---

### Task 6: Fix workspace state clearing mid-session (Bug 4)

**Files:**
- Modify: `ivy_lsp/mcp/tools/workspace.py:138-144`
- Test: `tests/test_tool_workspace.py` (add new test)

- [ ] **Step 1: Read the existing test file for context**

Run: `head -30 tests/test_tool_workspace.py` to understand existing patterns.

- [ ] **Step 2: Write the failing test**

Append to `tests/test_tool_workspace.py`:

```python
class TestHandleGetFallbackToPersisted:
    """_handle_get should fall back to persisted state when in-memory is None."""

    def test_get_returns_persisted_explicit_state(self, tmp_path):
        """When ctx.active_workspace is None but state file has explicit state,
        _handle_get should restore from the persisted file."""
        from ivy_lsp.core.workspace.active_workspace import ActiveWorkspace
        from ivy_lsp.mcp.tools.workspace import _handle_get

        # Create a persisted state file with explicit workspace
        state_file = tmp_path / ".ivy-workspace-state.json"
        ws = ActiveWorkspace(
            active_group="quic",
            active_layers={"quic", "quic_tests"},
            active_tests=[],
            granularity="protocol",
            set_by="explicit",
        )
        ws.save(str(state_file))

        # Mock context with None active_workspace but valid root
        class _MockCtx:
            active_workspace = None
            root = str(tmp_path)

        ctx = _MockCtx()
        result = _handle_get(ctx)

        assert result["status"] == "ok"
        assert result["active_group"] == "quic"
        assert result["set_by"] == "explicit"
        # Also verify in-memory state was restored
        assert ctx.active_workspace is not None
        assert ctx.active_workspace.active_group == "quic"

    def test_get_returns_cleared_when_no_state_file(self, tmp_path):
        """When both in-memory and persisted state are missing, return cleared."""
        from ivy_lsp.mcp.tools.workspace import _handle_get

        class _MockCtx:
            active_workspace = None
            root = str(tmp_path)

        result = _handle_get(_MockCtx())
        assert result["active_group"] is None
        assert result["set_by"] == "cleared"

    def test_get_returns_cleared_when_persisted_is_cleared(self, tmp_path):
        """When persisted state is also cleared, return cleared."""
        from ivy_lsp.core.workspace.active_workspace import ActiveWorkspace
        from ivy_lsp.mcp.tools.workspace import _handle_get

        state_file = tmp_path / ".ivy-workspace-state.json"
        ws = ActiveWorkspace.cleared()
        ws.save(str(state_file))

        class _MockCtx:
            active_workspace = None
            root = str(tmp_path)

        result = _handle_get(_MockCtx())
        assert result["active_group"] is None
        assert result["set_by"] == "cleared"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_tool_workspace.py::TestHandleGetFallbackToPersisted::test_get_returns_persisted_explicit_state -v`
Expected: FAIL — `active_group` is `None` because `_handle_get` doesn't check the state file.

- [ ] **Step 4: Implement the persisted state fallback**

In `ivy_lsp/mcp/tools/workspace.py`, replace `_handle_get` (lines 138-153):

```python
# OLD:
def _handle_get(ctx: Any) -> dict:
    """Handle action='get' for ivy_workspace."""
    ws = ctx.active_workspace
    if ws is None:
        from ivy_lsp.core.workspace.active_workspace import ActiveWorkspace

        ws = ActiveWorkspace.cleared()

    return {
        "status": "ok",
        "active_group": ws.active_group,
        "active_layers": sorted(ws.active_layers),
        "active_tests": ws.active_tests,
        "granularity": ws.granularity,
        "set_by": ws.set_by,
    }
```

With:

```python
# NEW:
def _handle_get(ctx: Any) -> dict:
    """Handle action='get' for ivy_workspace."""
    ws = ctx.active_workspace
    if ws is None:
        from ivy_lsp.core.workspace.active_workspace import ActiveWorkspace

        # Fall back to persisted state before returning cleared.
        state_path = os.path.join(ctx.root, ".ivy-workspace-state.json")
        if os.path.exists(state_path):
            ws = ActiveWorkspace.load(state_path)
            if ws.is_set():
                ctx.active_workspace = ws  # Restore in-memory state
                logger.info("Restored workspace from persisted state: %s", ws.active_group)
        if ws is None or not ws.is_set():
            ws = ActiveWorkspace.cleared()

    return {
        "status": "ok",
        "active_group": ws.active_group,
        "active_layers": sorted(ws.active_layers),
        "active_tests": ws.active_tests,
        "granularity": ws.granularity,
        "set_by": ws.set_by,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_tool_workspace.py -v`
Expected: ALL tests pass (existing + new).

- [ ] **Step 6: Run full test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -20`
Expected: No regressions.

- [ ] **Step 7: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp/tools/workspace.py tests/test_tool_workspace.py
git commit -m "fix: fall back to persisted workspace state in _handle_get when in-memory is None"
```

---

### Task 7: Final verification

- [ ] **Step 1: Run the full test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -q --timeout=30 2>&1 | tail -30`
Expected: All tests pass, no regressions from any of the 4 bug fixes.

- [ ] **Step 2: Verify all files changed**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && git diff --stat HEAD~5`

Expected changed files:
- `ivy_lsp/mcp/tools/__init__.py` (Bug 1a)
- `ivy_lsp/mcp/tools/analysis.py` (Bug 1b)
- `ivy_lsp/mcp/server.py` (Bug 1c)
- `ivy_lsp/lsp/workspace_symbols.py` (Bug 2)
- `ivy_lsp/lsp/document_symbols.py` (Bug 3)
- `ivy_lsp/mcp/tools/workspace.py` (Bug 4)
- `tests/test_safe_tool_semaphore.py` (new)
- `tests/test_workspace_symbols_filtering.py` (modified)
- `tests/test_tool_workspace.py` (modified)

- [ ] **Step 3: Re-run `/nct-health` to verify all 21 checks pass**

This requires restarting the Claude Code session so the MCP server and LSP restart with the fixes. After restart, run the health check to confirm the 14 failures are resolved.
